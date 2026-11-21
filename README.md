# BodySlide SliderSet & ShapeData Cleaner (MO2 Plugin)

A lightweight, native **Mod Organizer 2** plugin that helps you reclaim gigabytes of disk space and declutter BodySlide's *Batch Build* menu for both **Skyrim SE/AE** and **Fallout 4**—without breaking your load order.

## ✨ Key Features
* **Multi-Game Support (Skyrim SE & Fallout 4):** Auto-detects your active game in MO2 (or switch manually via the dropdown) with built-in body presets (`BHUNP`, `UUNP`, `UNP`, `TBD`, `COCO`, `3BA`, `CBBE` for Skyrim; `FusionGirl`, `JaneBod`, `AtomicBeauty`, `BodyTalk`, `ZE`, `3BBB`, `CBBE` for Fallout 4) plus custom tags.
* **Unused Body Types Cleaner:** Scans active and inactive mods in your MO2 directory for unused `.osp` SliderSets and `ShapeData` folders.
* **Orphaned Output Cleaner:** Cross-references generated `.nif` meshes in your BodySlide Output (or `Overwrite`) folder against active mods and SliderSets to identify leftover outfits from `[Disabled]` or `Uninstalled` mods.
* **Safe Backup or Permanent Delete:** Safely move files to `MO2\BodySlideCleaner_Backup` (preserving full folder structures) or delete them permanently, with automatic empty subfolder cleanup.
* **Smart Protection & Persistence:** Automatically protects `3BA` / `3BBB` files when unchecked, skips core body/head/skeleton meshes during output scans, and saves per-game settings between sessions.

## 📦 Installation
1. Download `BodySlideCleaner.py` and place it inside your Mod Organizer 2 plugins folder:
   ```text
   Mod Organizer 2\plugins\BodySlideCleaner.py
2. Restart Mod Organizer 2.
3. Launch from the top toolbar: Tools → BodySlide SliderSet & ShapeData Cleaner.
