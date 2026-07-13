class DashlaneAuditor < Formula
  desc "Audit and rotate stale Dashlane passwords"
  homepage "https://github.com/briandaviddavidson/dashlane-auditor"
  url "https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.5.0.tar.gz"
  sha256 "UPDATE_ON_RELEASE"
  license "MIT"

  include Language::Python::Shebang

  depends_on "dashlane/tap/dashlane-cli"
  depends_on "python@3.13"

  def install
    bin.install "dashlane-auditor"
    rewrite_shebang detected_python_shebang, bin/"dashlane-auditor"
    pkgshare.install "assist.py", "sites.json"
    (pkgshare/"sites").install Dir["sites/*.yaml"]
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/dashlane-auditor --version")
  end
end
