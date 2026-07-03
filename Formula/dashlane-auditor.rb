class DashlaneAuditor < Formula
  desc "Audit and rotate stale Dashlane passwords"
  homepage "https://github.com/briandaviddavidson/dashlane-auditor"
  url "https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.4.0.tar.gz"
  sha256 "7857d04a92f36bd5e6bcd391d0b64351ed17db1c4d9f33d9e32d17834fdff6fa"
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
