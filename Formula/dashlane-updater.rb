class DashlaneUpdater < Formula
  desc "Audit and rotate stale Dashlane passwords"
  homepage "https://github.com/briandaviddavidson/dashlane-auditor"
  url "https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_TARBALL_SHA256"
  license "MIT"

  depends_on "dashlane/tap/dashlane-cli"
  depends_on "python@3.13"

  def install
    bin.install "dashlane-updater"
    rewrite_shebang detected_python_shebang, bin/"dashlane-updater"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/dashlane-updater --version")
  end
end
