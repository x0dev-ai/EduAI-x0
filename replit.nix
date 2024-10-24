{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.pkg-config
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.glibcLocales
    pkgs.openssl
    pkgs.postgresql
  ];
}
