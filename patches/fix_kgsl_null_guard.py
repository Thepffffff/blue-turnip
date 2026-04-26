#!/usr/bin/env python3
"""
BLUE TURNIP — patches/fix_kgsl_null_guard.py
0004: KGSL syncobj null guard in vkQueueSubmit path.

Evidence (hs_err_pid5280.log):
  SIGSEGV at libvulkan_freedreno.so+0x8df724
  si_addr = 0x1a0 (NULL + 416)
  R4 = 0x0  <- NULL struct pointer dereferenced
  Stack: Renderer.submitFrame -> vkQueueSubmit -> tu_QueueSubmit
         -> kgsl_syncobj_wait (8 frames deep in KGSL path)

Root cause: timeline semaphore wait-point not yet submitted returns
NULL syncobj. Driver dereferences field at offset 0x1a0. Crash.
"""
import re, sys, os

path = "src/freedreno/vulkan/tu_kgsl.cc"
if not os.path.exists(path):
    print(f"SKIP: {path} not found")
    sys.exit(0)

src = open(path).read()

if "BLUE TURNIP: null guard" in src:
    print("SKIP: null guard already applied")
    sys.exit(0)

GUARD = r"""
   /* BLUE TURNIP: null guard for uninitialised KGSL syncobj.
    * A timeline semaphore wait-point not yet submitted returns NULL.
    * Dereferencing field at offset 0x1a0 crashes with SIGSEGV.
    * NULL syncobj = not yet signalled: skip wait, GPU ordering handles it.
    * Evidence: hs_err_pid5280.log si_addr=0x1a0, R4=0x0
    */
   if (!sync || sync->fd < 0)
      return VK_SUCCESS;
"""

pattern = r"(kgsl_syncobj_wait\s*\([^{]*\{)"
if re.search(pattern, src):
    patched = re.sub(pattern, r"\1" + GUARD, src, count=1)
    open(path, "w").write(patched)
    print("OK: null guard inserted into kgsl_syncobj_wait")
else:
    print("WARN: kgsl_syncobj_wait not found — check tu_kgsl.cc manually")
    sys.exit(1)
