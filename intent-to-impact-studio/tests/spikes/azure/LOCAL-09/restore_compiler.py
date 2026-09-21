"""Restore only the manifest-pinned compiler into the owned LOCAL-09 tool cache."""

from evidence import OWNED, SOURCE, ROOT, ReadOnlyRun, load, require, sha


def main():
    manifest = load(SOURCE / "toolchain.json")
    require(manifest["bicepVersion"] == "v0.47.16", "Unexpected toolchain change")
    binary = OWNED / manifest["binaryRelativeToLocal09Evidence"]
    require(binary.resolve().is_relative_to(OWNED.resolve()), "Tool path escaped LOCAL-09")
    run = ReadOnlyRun("compiler-restore")
    run.environment["AZURE_CONFIG_DIR"] = str(binary.parent.parent)
    run.environment["AZURE_BICEP_USE_BINARY_FROM_PATH"] = "false"
    run.receipt["credentialHandling"] = "Isolated tool-only CLI configuration; no login or credential copying."
    try:
        run.receipt["toolManifestSha256"] = sha(SOURCE / "toolchain.json")
        run.command("install-pinned-bicep", [*run.az_prefix, "bicep", "install", "--version", manifest["bicepVersion"]],
                    azure=False, timeout=240)
        require(binary.is_file(), "Compiler restore did not produce the exact owned binary")
        run.command("restored-bicep-version", [str(binary), "--version"], azure=False)
        run.receipt["compilerSha256"] = sha(binary)
        run.finish("pinned-local-tool-restored")
    except Exception as error:
        run.receipt["failure"] = str(error)
        run.finish("tool-restore-failed")
    print(str((run.root / "receipt.json").relative_to(ROOT)))
    return 0 if run.receipt["status"] == "pinned-local-tool-restored" else 1


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(main())
