#!/usr/bin/env python3
"""
BLUE TURNIP — patches/fix_kgsl_fd_init.py
0006: KGSL syncobj fd=0 guard (stdin fd corruption).

Evidence (hs_err_pid5280.log):
  R23 = 0x7249118110 -> all-zero valid memory (zero-filled heap page)
  Zero-initialised syncobj has fd=0, not fd=-1.
  fd=0 is stdin on Linux. sync_wait(0,...) blocks forever = GPU hang.
  Device: SM-A725F (Adreno 618, kernel 4.14) uses syncsource-based
  timeline emulation where every unsignalled semaphore goes this path.
"""
import re, sys, os

path = "src/freedreno/vulkan/tu_kgsl.cc"
if not os.path.exists(path):
    print(f"SKIP: {path} not found")
    sys.exit(0)

src = open(path).read()

if "BLUE TURNIP: fd=0 guard" in src:
    print("SKIP: fd=0 guard already applied")
    sys.exit(0)

FD_GUARD = r"""
   /* BLUE TURNIP: fd=0 guard.
    * Zero-initialised syncobj has fd=0 (stdin), not fd=-1 (invalid).
    * sync_wait(0,...) blocks on stdin forever, causing GPU hang.
    * Evidence: R23 in hs_err_pid5280 points to all-zero syncobj memory.
    * Treat fd=0 the same as fd=-1: semaphore not yet signalled, skip wait.
    */
   if (!sync || sync->fd <= 0)
      return VK_SUCCESS;
"""

# Replace the null guard from 0004 with the combined null+fd=0 guard
# (0004 uses fd < 0, we upgrade to fd <= 0 to cover fd=0 as well)
old_guard = r"if \(!sync \|\| sync->fd < 0\)\s*return VK_SUCCESS;"
if re.search(old_guard, src):
    patched = re.sub(
        old_guard,
        "if (!sync || sync->fd <= 0) /* BLUE TURNIP: fd=0 guard */ return VK_SUCCESS;",
        src,
        count=1
    )
    open(path, "w").write(patched)
    print("OK: upgraded null guard to also cover fd=0 (stdin)")
    sys.exit(0)

# Fallback: 0004 wasn't applied yet, insert full guard
pattern = r"(kgsl_syncobj_wait\s*\([^{]*\{)"
if re.search(pattern, src):
    patched = re.sub(pattern, r"\1" + FD_GUARD, src, count=1)
    open(path, "w").write(patched)
    print("OK: fd=0 guard inserted into kgsl_syncobj_wait (standalone)")
else:
    print("WARN: kgsl_syncobj_wait not found")
    sys.exit(1)
