//! The wallpaper adapter: any image becomes a readable terminal wallpaper in
//! the theme's colors.

use crate::store::{data_dir, find_theme, now_ms, parse_hex};
use image::imageops::{self, FilterType};
use image::{ImageFormat, Rgb, RgbImage};
use std::collections::hash_map::DefaultHasher;
use std::fs;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};

const SIZE: (u32, u32) = (2560, 1440);
const THUMB: (u32, u32) = (800, 450);
/// The image files Ambiance can read, by extension.
pub const FORMATS: [&str; 10] = ["png", "jpg", "jpeg", "gif", "bmp", "webp", "tif", "tiff", "ico", "tga"];
const MAX_INPUT: u64 = 64 * 1024 * 1024;

fn hex(value: Option<&str>) -> [f32; 3] {
    value.and_then(parse_hex).unwrap_or([12, 12, 18]).map(f32::from)
}

/// Removes the user's earlier wallpapers once the new one is written.
fn remove_others(dir: &Path, keep: &Path) {
    for old in fs::read_dir(dir).into_iter().flatten().flatten() {
        if old.path() != keep {
            let _ = fs::remove_file(old.path());
        }
    }
}

/// `intensity` (0 to 1): how strong the tint and the darkening are.
pub fn adapt(id: &str, source: &Path, intensity: f64) -> Result<PathBuf, String> {
    let size = fs::metadata(source).map(|m| m.len()).map_err(|_| "image not found")?;
    if size > MAX_INPUT {
        return Err("image too large (64 MB at most)".into());
    }
    let extension = source.extension().and_then(|e| e.to_str()).unwrap_or_default().to_lowercase();
    if !FORMATS.contains(&extension.as_str()) {
        return Err("accepted formats: PNG, JPG, WebP, GIF, BMP, TIFF, ICO, TGA".into());
    }

    let dir = data_dir().join("overrides").join(id);
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;

    // An animated GIF keeps its animation: Windows Terminal shows it as is, and
    // the profile's opacity blends it into the theme's colors.
    if extension == "gif" {
        let target = dir.join(format!("wallpaper-{}.gif", now_ms()));
        fs::copy(source, &target).map_err(|e| e.to_string())?;
        remove_others(&dir, &target);
        return Ok(target);
    }

    let theme = find_theme(id).ok_or("theme not found")?;
    let background = hex(theme["terminal"]["background"].as_str());
    let accent = hex(theme["colors"]["accent"].as_str());
    let strength = intensity.clamp(0.0, 1.0) as f32;

    let picture = image::open(source).map_err(|e| format!("unreadable image: {e}"))?.to_rgb8();
    let (cx, cy, cw, ch) = crop(picture.dimensions());
    let picture = imageops::resize(&imageops::crop_imm(&picture, cx, cy, cw, ch).to_image(), SIZE.0, SIZE.1, FilterType::Lanczos3);
    let picture = imageops::blur(&picture, 1.2 + strength * 1.5);

    let (w, h) = SIZE;
    let mut out = RgbImage::new(w, h);
    for (x, y, pixel) in picture.enumerate_pixels() {
        let fx = x as f32 / w as f32;
        let fy = y as f32 / h as f32;
        let luminance = (0.299 * pixel[0] as f32 + 0.587 * pixel[1] as f32 + 0.114 * pixel[2] as f32) / 255.0;
        // The theme's tones: shadows toward the background, highlights toward the accent.
        let tone: [f32; 3] = std::array::from_fn(|i| background[i] + (accent[i] - background[i]) * luminance.powf(1.6) * 0.55);
        let mix = 0.25 + 0.45 * strength;
        let left = (1.0 - fx * 1.6).clamp(0.0, 1.0).powf(1.5) * (0.35 + 0.35 * strength);
        let dx = fx - 0.62;
        let dy = fy - 0.45;
        let vignette = ((dx * dx + dy * dy).sqrt() / 0.75).min(1.2).powi(2) * 0.4;
        // The bottom too: Claude Code's banner and prompt sit there.
        let bottom = ((fy - 0.6) / 0.4).clamp(0.0, 1.0).powf(1.2) * 0.5 * (1.25 - fx).clamp(0.3, 1.0);
        let darken = 1.0 - (left + vignette + bottom + 0.2 * strength).min(0.88);
        let value: [u8; 3] = std::array::from_fn(|i| {
            let tinted = pixel[i] as f32 * (1.0 - mix) + tone[i] * mix;
            (tinted * darken).clamp(0.0, 255.0) as u8
        });
        out.put_pixel(x, y, Rgb(value));
    }

    let target = dir.join(format!("wallpaper-{}.jpg", now_ms()));
    let file = fs::File::create(&target).map_err(|e| e.to_string())?;
    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(std::io::BufWriter::new(file), 90);
    encoder.encode_image(&out).map_err(|e| e.to_string())?;
    drop(encoder);
    remove_others(&dir, &target);
    Ok(target)
}

/// The largest centered 16:9 rectangle in the image: (x, y, width, height).
fn crop((w, h): (u32, u32)) -> (u32, u32, u32, u32) {
    let target = 16.0 / 9.0;
    if w as f32 / h as f32 > target {
        let nw = (h as f32 * target) as u32;
        ((w - nw) / 2, 0, nw, h)
    } else {
        let nh = (w as f32 / target) as u32;
        (0, (h - nh) / 2, w, nh)
    }
}

/// A small JPEG copy of a wallpaper for the app's previews, cached under
/// ~/.ambiance/cache/thumbs: sending every 2560 × 1440 wallpaper to the window
/// made the app slow to open. A changed file gets a new copy.
pub fn thumbnail(source: &Path) -> Result<PathBuf, String> {
    let meta = fs::metadata(source).map_err(|_| "image not found")?;
    let mut hasher = DefaultHasher::new();
    source.hash(&mut hasher);
    meta.len().hash(&mut hasher);
    meta.modified().ok().hash(&mut hasher);
    let dir = data_dir().join("cache").join("thumbs");
    let target = dir.join(format!("{:016x}.jpg", hasher.finish()));
    if target.is_file() {
        return Ok(target);
    }
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let picture = image::open(source).map_err(|e| format!("unreadable image: {e}"))?;
    let small = picture.thumbnail(THUMB.0, THUMB.1).to_rgb8();
    // Written aside then renamed, so a half-written copy is never served.
    let partial = target.with_extension("part");
    let file = fs::File::create(&partial).map_err(|e| e.to_string())?;
    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(std::io::BufWriter::new(file), 82);
    encoder.encode_image(&small).map_err(|e| e.to_string())?;
    drop(encoder);
    fs::rename(&partial, &target).map_err(|e| e.to_string())?;
    Ok(target)
}

/// Downloads an image from a web link, to adapt it like a local file. The
/// format is read from the file itself, not from the link, which often has
/// no extension (or a misleading one).
pub fn download(url: &str) -> Result<PathBuf, String> {
    let url = url.trim();
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return Err("paste a link starting with https://".into());
    }
    let config = ureq::Agent::config_builder()
        .timeout_global(Some(std::time::Duration::from_secs(30)))
        .user_agent("Ambiance (wallpaper import)")
        .build();
    let mut response = ureq::Agent::new_with_config(config).get(url).call().map_err(|e| format!("download failed: {e}"))?;
    let bytes = response.body_mut().with_config().limit(MAX_INPUT).read_to_vec().map_err(|e| match e {
        ureq::Error::BodyExceedsLimit(_) => "image too large (64 MB at most)".to_string(),
        e => format!("download failed: {e}"),
    })?;
    let extension = match image::guess_format(&bytes) {
        Ok(ImageFormat::Png) => "png",
        Ok(ImageFormat::Jpeg) => "jpg",
        Ok(ImageFormat::Gif) => "gif",
        Ok(ImageFormat::WebP) => "webp",
        Ok(ImageFormat::Bmp) => "bmp",
        Ok(ImageFormat::Tiff) => "tiff",
        Ok(ImageFormat::Ico) => "ico",
        Ok(ImageFormat::Tga) => "tga",
        Ok(format) => return Err(format!("{format:?} images are not supported yet")),
        // Most often a web page: the link of the page, not of the image.
        Err(_) => return Err("this link is not an image: right-click the image, then \"Copy image address\"".into()),
    };
    let dir = data_dir().join("cache").join("downloads");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let target = dir.join(format!("download-{}.{extension}", now_ms()));
    fs::write(&target, &bytes).map_err(|e| e.to_string())?;
    Ok(target)
}
