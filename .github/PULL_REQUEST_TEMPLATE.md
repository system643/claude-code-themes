<!-- Thanks for contributing! Keep the checklist that matches your change and delete the other one. -->

## What and why

<!-- One or two sentences. Link the issue if there is one: "Closes #12". -->

## Theme

- [ ] `python scripts/build_gallery.py --check` passes
- [ ] The folder name and `id` match (lowercase letters, digits, hyphens)
- [ ] Tried with `/ambiance <id>` in a real session: banner, quotes and terminal colors are readable
- [ ] Wallpaper is a 2560 × 1440 JPG under 1 MB (or a GIF under 8 MB); sounds are under a second
- [ ] Images, sounds, art and quotes are original, or under a free license and credited in `assets/CREDITS.md`

## Code

- [ ] Plugin (`plugin/hooks/`): `claude plugin validate .` and `claude plugin test plugin` pass, with tests for the change
- [ ] App frontend (`app/src/`): `npm run build` passes in `app/`
- [ ] App backend (`app/src-tauri/`): `cargo clippy --all-targets -- -D warnings` and `cargo test` pass
- [ ] Shaders: regenerated with `scripts/build_shaders.py`, and `python3 scripts/check_glsl.py` passes
- [ ] `CHANGELOG.md` updated under `[Unreleased]` if users will notice the change

Tested on: <!-- Windows / macOS / Linux, and which terminal -->

<!-- Screenshots or a short GIF help a lot for anything visual. -->
