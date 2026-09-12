# tools

Binaries the library looks for here. They are not in the repository; fetch them once.

- `freerouting-2.4.1.jar` from the FreeRouting releases (https://github.com/freerouting/freerouting/releases).
  Used by the `autoroute` tool; the layer's own routers do not need it.
- `jre/` an Eclipse Temurin JRE 25 for Windows x64 (https://adoptium.net), unzipped so that `jre/bin/java.exe`
  exists. FreeRouting runs on it; a system Java on the PATH works too.

`kicad_doctor` reports what it finds.
