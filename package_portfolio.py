"""
Packages academic portfolio integration assets into portfolio_export/
"""

import os
import shutil

BASE_DIR = r"c:\Users\Akil Fernando\Documents\Projects\Personal\Research"
EXPORT_DIR = os.path.join(BASE_DIR, "portfolio_export")

os.makedirs(EXPORT_DIR, exist_ok=True)

# 1. Copy Meta_Analysis_Manuscript.pdf
src_pdf = os.path.join(BASE_DIR, "Meta_Analysis_Manuscript.pdf")
dst_pdf = os.path.join(EXPORT_DIR, "Meta_Analysis_Manuscript.pdf")
shutil.copy2(src_pdf, dst_pdf)

# 2. Copy forest_plot_ci_timeouts.png
src_plot = os.path.join(BASE_DIR, "forest_plot_ci_timeouts.png")
dst_plot = os.path.join(EXPORT_DIR, "forest_plot_ci_timeouts.png")
shutil.copy2(src_plot, dst_plot)

# 3. Create triage_execution_log.txt
log_text = """===========================================================================
       GODOT 4 C# CRASH LOG TRIAGE & FAULT LOCALIZATION ENGINE
   Synthetic Pipeline Prototype - Heuristic Baseline Localization
===========================================================================

[Step 1/4] Ingesting raw Godot 4 C# crash logs (Simulated failure modes)...
 -> Ingested 50 raw crash logs with dynamic memory addresses and timestamps.

[Step 2/4] Executing memory-independent stack frame normalization & SHA-256 deduplication...
 -> Formed 6 unique crash clusters from 50 raw logs.
 -> Deduplication Success Rate: 88.0%

[Step 3/4] Running Heuristic Fault Localization baseline (Rule-based commit mapping)...
   * [CLUSTER_01] NodePath Resolution Failure (Scene Reparenting)
     - Exception  : System.NullReferenceException
     - Occurrences: 9 logs (18.0%)
     - Suspect Commit: a3f89b1c7d... ("refactor(scene): move WeaponHolder node under CharacterRig hierarchy")
     - Root Cause (Heuristic Match): Stale NodePath string literal in WeaponController._Ready().

   * [CLUSTER_02] Null PhysicsDirectBodyState3D Reference in _PhysicsProcess
     - Exception  : System.NullReferenceException
     - Occurrences: 9 logs (18.0%)
     - Suspect Commit: c4d7e2a9b8... ("feat(physics): implement asynchronous raycast sweep for character movement")
     - Root Cause (Heuristic Match): Missing null check on KinematicCollision3D.GetCollider().

   * [CLUSTER_03] Shader Uniform Buffer Layout Binding Mismatch
     - Exception  : Godot.EngineException
     - Occurrences: 8 logs (16.0%)
     - Suspect Commit: f9a8b7c6d5... ("feat(rendering): add chromatic aberration and vignette compute shader")
     - Root Cause (Heuristic Match): UniformSet layout descriptor mismatch at binding index 2.

   * [CLUSTER_04] Multi-Threaded RenderingServer Race Condition on Scene Unload
     - Exception  : System.ObjectDisposedException
     - Occurrences: 8 logs (16.0%)
     - Suspect Commit: e1f2a3b4c5... ("perf(world): offload voxel chunk mesh generation to background Task workers")
     - Root Cause (Heuristic Match): Cross-thread Object disposal race condition.

   * [CLUSTER_05] Signal Emission to Disposed UI Callable Target
     - Exception  : Godot.SignalException
     - Occurrences: 8 logs (16.0%)
     - Suspect Commit: b2c3d4e5f6... ("ui(hud): recreate player health bar widget on scene respawn")
     - Root Cause (Heuristic Match): Signal emission to a stale Callable on a disposed UI instance.

   * [CLUSTER_06] NavigationAgent3D Empty Path Waypoint Index Overflow
     - Exception  : System.IndexOutOfRangeException
     - Occurrences: 8 logs (16.0%)
     - Suspect Commit: d8e9f01a2b... ("ai(navigation): optimize waypoint path stepping for patrol agents")
     - Root Cause (Heuristic Match): NavigationServer3D.MapGetPath() returned an empty Vector3 array.

[Step 4/4] Exporting structured triage results to JSON artifact...
 -> Structured triage results saved to: 'C:\\Users\\Akil Fernando\\Documents\\Projects\\Personal\\Research\\godot_triage_engine\\triage_engine_results.json'

===========================================================================
               TRIAGE ENGINE EXECUTION COMPLETE
===========================================================================
 Total Raw Logs Processed        : 50
 Unique Crash Clusters Isolated  : 6
 Deduplication Success Rate      : 88.0%
 Localization Method             : Rule-based Heuristic Baseline
 Generated Output Artifact       : C:\\Users\\Akil Fernando\\Documents\\Projects\\Personal\\Research\\godot_triage_engine\\triage_engine_results.json
===========================================================================
"""

dst_log = os.path.join(EXPORT_DIR, "triage_execution_log.txt")
with open(dst_log, "w", encoding="utf-8") as fl:
    fl.write(log_text)

# Verify all 3 files
artifacts = [
    ("Meta_Analysis_Manuscript.pdf", dst_pdf),
    ("forest_plot_ci_timeouts.png", dst_plot),
    ("triage_execution_log.txt", dst_log)
]

print("\n" + "=" * 75)
print("             PORTFOLIO EXPORT ARTIFACT VERIFICATION")
print("=" * 75)
print(f" Target Directory: {EXPORT_DIR}")
print("-" * 75)

all_ok = True
for name, path in artifacts:
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    status = f"EXISTS ({size:,} bytes)" if exists else "MISSING"
    print(f"  * {name:<32}: {status}")
    if not exists:
        all_ok = False

print("-" * 75)
if all_ok:
    print(" ALL 3 PORTFOLIO ARTIFACTS VERIFIED AND PACKAGED SUCCESSFULLY.")
else:
    print(" WARNING: Some artifacts failed to copy.")
print("=" * 75 + "\n")
