# Technical notes — Double Cast (PS1, SCPS-10053/10054)

All addresses refer to the Japanese EXE `SCPS_100.53` (CD1); CD2's `SCPS_100.54` has the
same layout. `gp = 0x80077AAC`.

## Disc

* Mode 2 Form 1, single data track; XA/STR streams are interleaved.
* The game locates files through its own table `\VFILE.INF` (from `SSX.CNF`), not only ISO9660.
  Record = 28 bytes: `u16 type, char name[12], u16 flags, u32 lba, u32 payload, u32 size`.
  For files with an `83 A1` header `payload` must equal header field `+0x0C`, otherwise the
  game hangs while loading.
* Rebuild (`tools/ydbuild.py`): files that grow are moved to the end of the image; ISO9660
  directory records, `VFILE.INF` and the PVD volume size are updated; EDC/ECC recomputed
  (`tools/disc.py`).

## Scripts (`*.SSC`)

Header `83 A1 00 01`, 12 × u32: `[2]` file size, `[3]` code+strings size, `[4]` code offset
(0x30), `[6]` code length, `[7]` string table length. Strings are NUL-terminated, Shift-JIS
with half-width kana (bytes `A1..DF`) for hiragana.

Stack VM (`0x8001709C` statements, `0x800175D0` expressions). Operand sizes used by the
linear tokenizer (`tools/ssc.py`):

| Opcode | Operand bytes |
|---|---|
| `0B 0C 10 12 13 14 50` | 1 |
| `0D 0E 11 1A 22` | 2 (`1A` = string offset in the table) |
| `0F` | 4 |
| `1E`, `80..8B` | jump target: `(op&3)` 0/1 → 1 byte, 2 → 2, 3 → 3 |
| `90 91` | 1 + target(size from that byte) |
| `92` | 2 + target |
| `E0..FF` | 1 (extended function number) |

The tokenizer covers every script on both discs exactly, and every `1A` operand points to a
string start, so string tables can be rebuilt freely.

Message defaults live in a script block in `STARTUP.SSC`/`MAIN.SSC`
(`vol 0x46/0x5F/0x7F …`); variable `0x38A` is the message mode
(0 voice only, 1 text+voice, 2 text only). The build changes its `push 0` (`09`) to `push 1` (`0A`).

## Text engine

* Renderer loop `0x80028258…`, control dispatch table `0x8001062C` for `0x21..0x7C`
  (after `toupper`). ASCII `! # $ % & * / : @ | C D Q S T W` are control codes;
  `$` = newline, `!` = clear window, `{ … }` = raw mode. `A0 xx` = escaped literal byte.
* Glyphs: `0x80029A44`. Codes `< 0x100` → `FONTA.DAT` (6×12 1bpp, 9 bytes/glyph,
  `0x20..0x7F`, `0xA0..0xDF`), drawn **11 rows high**; double-byte → `FONTD.DAT` (12 px).
* `0x80029224` converted half-width kana to SJIS hiragana; patched to `jr ra / move v0,a0`
  so `A0..DF` are drawn from `FONTA.DAT` (Latin/Cyrillic glyph slots).
* Word wrap hook (`tools/wordwrap.py`, assembled by `tools/mini_asm.py`):
  `0x800289FC → j 0x8002922C` (free space in the old converter). On a space it measures the
  next word; if `x + 18 + width > struct+0x112` it calls the engine newline routine
  `0x80028C04(s3, &x, &y, 1)` and drops the space.
  Mind the R3000 load delay slot when editing the hook.
* Text window struct: `+0x112` line width (264), `+0x116` half-width advance (6).
  Three lines are visible; longer messages scroll and lose their first lines.
* A message can consist of several strings (one per voice clip); they are appended to the
  current line, so continuation strings must start with a space.

## Encodings used by the build

| | Russian | English |
|---|---|---|
| Upper case | `Б..Я → A1..BF`, `А → 7F` | `A..Z → A1..BA` |
| Lower case | `а..я → C0..DF` | `a..z → C0..D9` |
| `!` / `:` | `60` / `5E` (glyph slots) | same |
| `* / & % # @` | — | `BB BC BD BE BF DB` |

## PSP English patch

The PSP version uses the same SSC engine. English strings are encoded as
`A..Z → A6..BF`, `a..z → C0..D9`, space `DA`, punctuation and digits as `82 xx`
pseudo-SJIS codes (`tools/psp_en.py: decode_en`). Strings are paired with the Japanese ones
by aligning the bytecode token streams of the original and patched scripts.

## Not done yet

* Graphics (`SYSTEM2/TITLE.BIN`, `SUBWIN.DAT`, `*.GPX`): compressed with a codec that has not
  been identified. `research/glz.py` implements the LZ decoder at `0x80041340`, which is
  used at boot but does **not** match the GPX/TITLE.BIN data.

## Research helpers (`research/`)

* `lr.py` — minimal libretro frontend (ctypes) for PCSX-ReARMed: run frames, press buttons,
  screenshots, save states, RAM access. Works with the HLE BIOS.
* `pcsx_rearmed-trace.diff` — adds to the interpreter: PC histogram (`g_pctrace`),
  CD DMA log with MSF (`g_dmalog`), memory-read watch (`g_wlo/g_whi/g_rtrace`),
  register-dump breakpoint (`g_bp_pc`). Build with `make -f Makefile.libretro`
  and run with `pcsx_rearmed_drc=disabled`.
* `mdis.py` — capstone disassembly / xref helpers for the EXE.
