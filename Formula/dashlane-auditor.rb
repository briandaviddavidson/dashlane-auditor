class DashlaneAuditor < Formula
  desc "Audit and rotate stale Dashlane passwords"
  homepage "https://github.com/briandaviddavidson/dashlane-auditor"
  url "https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "14f77ac162bd50a9a6e8b93ae97ea0c1a95c6a5ed1a20be2673bbbe751acd48a"
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
