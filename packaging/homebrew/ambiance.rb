# Homebrew cask template. After a release: replace the version and the .dmg's
# sha256, then publish it in a tap (the sytem643/homebrew-tap repository):
#   brew install --cask sytem643/tap/ambiance
cask "ambiance" do
  version "<VERSION>"
  sha256 "<SHA256>"

  url "https://github.com/sytem643/claude-code-themes/releases/download/v#{version}/Ambiance_#{version}_universal.dmg"
  name "Ambiance"
  desc "A different theme for every Claude Code session"
  homepage "https://github.com/sytem643/claude-code-themes"

  app "Ambiance.app"

  zap trash: "~/.ambiance"
end
