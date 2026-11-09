# YaruDora Series Vol.1: Double Cast — PS1 translation tools

Tools that port the English fan translation of the PSP remake
(*Yarudora Portable: Double Cast*, translation by **Cargodin & Esperknight**,
[romhacking.net #5777](https://www.romhacking.net/translations/5777/)) to the original
PlayStation release (SCPS-10053/10054), plus a kit for a Russian translation.

This repository contains **code only**. No game data, no extracted script and no
translation text are included: everything is built locally from your own disc images
and from the official PSP patch.

[Русская версия README](README_RU.md) · [Technical notes](docs/TECHNICAL.md)

## Requirements

* Python 3.8+ with `openpyxl` (`pip install openpyxl`)
* `xdelta3` in `PATH`
* Your own images: PS1 *Double Cast* CD1/CD2 (`.bin`, Mode2/2352, single track) and the
  PSP ISO *Yarudora Portable: Double Cast*, plus `patch.xdelta3` from the English PSP patcher.

## English (port of the PSP fan translation)

```
python3 port_english.py CD1.bin CD2.bin "Yarudora Portable - Double Cast.iso" patch.xdelta3 out/
```

Output: patched `Double Cast (CD1) [EN].bin/.cue`, the same for CD2, and
`DoubleCast_CDx_EN_PS1.xdelta` patches against the original images.
`warnings_en.txt` lists the lines longer than three rows of the message window.

What the build does:

* applies the English patch to the PSP ISO and maps every Japanese string of the PSP
  scripts to its English counterpart (token-aligned SSC bytecode, ~98% coverage on PS1);
* writes the English text into the PS1 `SCNxxx.SSC` scripts (string table rebuilt, pointers fixed);
* puts a 6×12 Latin font into `FONTA.DAT` (X11 *misc-fixed*, public domain);
* patches the EXE: half-width glyphs are drawn from `FONTA.DAT`, the text engine wraps by words,
  the interface strings (memory card, options) are translated;
* makes *Text + Voice* the default message mode (the original default is voice only).

Graphics with Japanese text (title menu buttons, options menu, controls screen) are not
translated yet.

## Russian

```
python3 extract.py  CD1.bin CD2.bin script_ru.xlsx         # table: Japanese text + empty Russian column
python3 make_patch.py CD1.bin CD2.bin script_ru.xlsx out/  # build images and xdelta patches
```

Empty cells stay Japanese (still readable). The interface and character names are
already translated. See [README_RU.md](README_RU.md) for the translation rules.

## Layout

| Path | What |
|---|---|
| `port_english.py` | English port build |
| `extract.py`, `make_patch.py` | Russian translation table / build |
| `tools/` | SSC script format, disc rebuild (ISO9660, `VFILE.INF`, EDC/ECC), text codecs, font, EXE hooks |
| `research/` | Reverse-engineering helpers: libretro frontend for PCSX-ReARMed, MIPS disassembly, CD DMA / PC / memory-read tracing patch |
| `docs/TECHNICAL.md` | Formats and patch details |

## Credits

* English translation: **Cargodin & Esperknight** (PSP patch). Please respect their wishes
  regarding distribution of patches derived from their work.
* Font glyphs: X11 *misc-fixed* 6×12 (public domain).
