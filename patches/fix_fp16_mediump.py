#!/usr/bin/env python3
"""
BLUE TURNIP — patches/fix_fp16_mediump.py
0008 (part 2): fp16/mediump lowering in ir3 compiler.

Adreno 6xx/7xx has native fp16 ALU units running at 2x fp32 throughput.
The vendor driver promotes mediump/relaxedPrecision operations to fp16
aggressively. Mesa's nir_lower_mediump_vars pass does this but requires
explicit enabling in the compiler pipeline.
"""
import re, sys, os

for path in ["src/freedreno/vulkan/tu_shader.cc",
             "src/freedreno/vulkan/tu_shader.c"]:
    if os.path.exists(path):
        break
else:
    print("SKIP: tu_shader.cc not found")
    sys.exit(0)

src = open(path).read()

if "BLUE TURNIP: fp16" in src:
    print("SKIP: fp16 patch already applied")
    sys.exit(0)

MEDIUMP_PASS = """
   /* BLUE TURNIP: fp16 mediump lowering.
    * Adreno 6xx/7xx fp16 ALUs run at 2x fp32 throughput.
    * Promote mediump-eligible temporaries and shared memory to fp16
    * storage, matching vendor driver behaviour on relaxedPrecision ops.
    * Safe: Vulkan explicitly permits fp16 for RelaxedPrecision values.
    */
   nir_lower_mediump_vars(nir, nir_var_function_temp | nir_var_mem_shared);
"""

# Find where NIR optimisation passes are called in tu_shader.cc
# Typical pattern: after nir_validate_shader or nir_split_var_copies
targets = [
    r"(nir_validate_shader\s*\([^;]+;\s*\n)",
    r"(nir_split_var_copies\s*\([^;]+;\s*\n)",
    r"(NIR_PASS_V\s*\(\s*nir\s*,\s*nir_opt_copy_prop_vars\s*\)[^;]*;\s*\n)",
]

patched = False
for pattern in targets:
    if re.search(pattern, src):
        src = re.sub(pattern, r"\1" + MEDIUMP_PASS, src, count=1)
        patched = True
        print(f"OK: fp16 mediump lowering pass inserted (pattern: {pattern[:40]}...)")
        break

if not patched:
    print("WARN: could not find NIR opt insertion point in tu_shader.cc")
    print("      fp16 lowering not applied — ALU throughput gap remains")
    sys.exit(1)

open(path, "w").write(src)
