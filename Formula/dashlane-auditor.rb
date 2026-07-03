class DashlaneAuditor < Formula
  desc "Audit and rotate stale Dashlane passwords"
  homepage "https://github.com/briandaviddavidson/dashlane-auditor"
  url "https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.3.1.tar.gz"
  sha256 "c08ce61220413dce778d45b284659e53d8cf7d40b77692343e0e5e7876fd736a"
  license "MIT"

  include Language::Python::Shebang

  depends_on "dashlane/tap/dashlane-cli"
  depends_on "python@3.13"

  def install
    bin.install "dashlane-auditor"
    rewrite_shebang detected_python_shebang, bin/"dashlane-auditor"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/dashlane-auditor --version")
  end
end
