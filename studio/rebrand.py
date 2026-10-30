#!/usr/bin/env python3
"""Apply the klmat (Creative Studio) branding on top of upstream WordCraft.

Only user-visible text is rebranded; crate names, the file format and other internals keep their
upstream names so `git merge upstream/main` stays easy. The script is idempotent: after merging
upstream, resolve any conflicts in favour of upstream and run it again.

    python3 studio/rebrand.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = 'klmat'
REPO = 'https://github.com/7mz410/CreativeStudio-klmat'
SITE = 'https://studio.creative.ps'
APP_SITE = 'https://klmat.studio.creative.ps'
# Persisted names and legal lines; renaming them would lose settings or misstate copyright.
KEEP = ('by the ArtCraft team', 'Application Support/WordCraft', '/roaming/WordCraft', 'the WordCraft authors', 'WordCraft contributors', 'WORDCRAFT_')

# (file, upstream text, our text[, marker meaning "already applied"]). The upstream text may also
# be found in its renamed form (after the general rename below).
RULES = [
    # No community Discord: the button is off by default, and "community" means Creative Studio.
    ('crates/ui-egui/src/lib.rs', '            show_discord: true,', '            show_discord: false,'),
    ('crates/ui-egui/src/lib.rs', 'self.canvas.open_url = Some("https://discord.gg/artcraft".into());', f'self.canvas.open_url = Some("{SITE}".into());'),
    ('crates/ui-egui/src/ribbon.rs', 'big(ui, app, "discord", "Community\\nDiscord", "ui.discord", json!({}), false);', 'big(ui, app, "help", "Creative\\nStudio", "ui.discord", json!({}), false);'),
    ('crates/ui-egui/src/backstage.rs', '[("About", "about"), ("Discord community", "discord")]', '[("About", "about"), ("Creative Studio", "discord")]'),
    ('crates/ui-egui/src/keytips.rs', 'c("Community Discord", "ui.discord")', 'c("Creative Studio", "ui.discord")'),
    ('crates/ui-egui/src/chrome.rs', 'tl!("Join the ArtCraft community on Discord")', 'tl!("Creative Studio")'),
    # About.
    ('crates/ui-egui/src/dialogs/dispatch.rs', '"A free, open-source word processor written from scratch in Rust.\\nPart of the Crafting Apps from the ArtCraft team."',
     '"A free, open-source word processor, part of the Creative Studio suite.\\nBuilt on WordCraft by the ArtCraft team."'),
    ('crates/ui-egui/src/dialogs/dispatch.rs', 'ui.hyperlink_to(tl!("getartcraft.com/apps/wordcraft"), "https://getartcraft.com/apps/wordcraft");',
     f'ui.hyperlink_to(tl!("klmat.studio.creative.ps"), "{APP_SITE}");'),
    ('crates/ui-egui/src/dialogs/dispatch.rs', '                    ui.hyperlink_to(tl!("Join us on Discord: discord.gg/artcraft"), "https://discord.gg/artcraft");\n', ''),
    ('crates/ui-egui/src/dialogs/dispatch.rs', 'ui.hyperlink_to(tl!("Source code: github.com/storytold/wordcraft"), "https://github.com/storytold/wordcraft");',
     f'ui.hyperlink_to(tl!("Source code: github.com/7mz410/CreativeStudio-klmat"), "{REPO}");'),
    # Web page and packages.
    ('apps/wordcraft-web/index.html', '<title>WordCraft</title>', f'<title>{NAME}</title>'),
    ('apps/wordcraft-web/index.html', 'Loading WordCraft&hellip;', f'Loading {NAME}&hellip;', 'ss-scene'),  # or the splash
    ('packaging/macos/Info.plist.in', '<string>ai.storyteller.wordcraft</string>', '<string>ps.creative.studio.klmat</string>'),
    ('packaging/windows/wordcraft.wxs', '<Property Id="ARPURLINFOABOUT" Value="https://getartcraft.com/apps/wordcraft" />', f'<Property Id="ARPURLINFOABOUT" Value="{APP_SITE}" />'),
    ('packaging/windows/wordcraft.wxs', '<Property Id="ARPURLUPDATEINFO" Value="https://getartcraft.com/apps/wordcraft" />', f'<Property Id="ARPURLUPDATEINFO" Value="{REPO}/releases" />'),
    ('packaging/windows/wordcraft.wxs', '<Property Id="ARPHELPLINK" Value="https://discord.gg/artcraft" />', f'<Property Id="ARPHELPLINK" Value="{REPO}/issues" />'),
    ('packaging/linux/nfpm.yaml', 'homepage: https://getartcraft.com/apps/wordcraft', f'homepage: {APP_SITE}'),
]
# Text in string literals and catalogs, before the general rename.
LITERALS = [
    ('Join the ArtCraft community on Discord', 'Creative Studio'),
]
STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')


def rename(lit: str) -> str:
    for a, b in LITERALS:
        lit = lit.replace(a, b)
    if any(k in lit for k in KEEP):
        return lit
    return lit.replace('WordCraft', NAME)


def renamed_code(text: str) -> str:
    return STRING.sub(lambda m: rename(m.group(0)), text)


def apply_rules() -> list:
    changed = []
    for rel, a, b, *marker in RULES:
        p = ROOT / rel
        s = p.read_text(encoding='utf-8')
        if marker and marker[0] in s:
            continue
        if a not in s and renamed_code(a) in s:
            a = renamed_code(a)  # the general rename got there first
        if a not in s or (b and a in b and b in s):
            if not b or b in s or renamed_code(b) in s:
                continue  # already applied
            print(f'warning: {rel}: upstream text not found (did upstream change it?): {a[:70]!r}')
            continue
        p.write_text(s.replace(a, b), encoding='utf-8')
        changed.append(rel)
    return changed


def rename_sources() -> list:
    changed = []
    for p in sorted((ROOT / 'crates/ui-egui').rglob('*.rs')) + [q for q in sorted((ROOT / 'crates/engine').rglob('*.rs')) if not q.name.startswith('tests')] + sorted((ROOT / 'apps').rglob('*.rs')):
        s = p.read_text(encoding='utf-8')
        o = renamed_code(s)
        if o != s:
            p.write_text(o, encoding='utf-8')
            changed.append(p.relative_to(ROOT).as_posix())
    # Catalog rows are `context<TAB>English<TAB>translation`: rename both text columns alike.
    for p in sorted((ROOT / 'crates/ui-egui/src/i18n').glob('*.tsv')):
        s = p.read_text(encoding='utf-8')
        rows = []
        for line in s.split('\n'):
            cells = line.split('\t')
            if len(cells) >= 3 and not line.startswith('#'):
                line = '\t'.join([cells[0], *(rename(c) for c in cells[1:])])
            rows.append(line)
        o = '\n'.join(rows)
        if o != s:
            p.write_text(o, encoding='utf-8')
            changed.append(p.relative_to(ROOT).as_posix())
    plist = ROOT / 'packaging/macos/Info.plist.in'
    s = plist.read_text(encoding='utf-8')
    o = re.sub(r'(<key>CFBundle(?:Display|Executable)?Name</key>\s*<string>)WordCraft(</string>)', rf'\g<1>{NAME}\2', s)
    if o != s:
        plist.write_text(o, encoding='utf-8')
        changed.append('packaging/macos/Info.plist.in')
    return changed


def main():
    changed = apply_rules() + rename_sources()
    for c in sorted(set(changed)):
        print('rebranded', c)


# Creative Studio: the macOS app folder in the .dmg and the volume name carry our name
# (packaging/macos/package.sh). Bundle and binary names inside the package stay as upstream has them.
PACKAGING_NAMES = {
    'packaging/macos/package.sh': [
        ('WordCraft.app', 'klmat.app'),
        ('-volname "WordCraft"', '-volname "klmat"'),
        ('-hfs-volume-name "WordCraft"', '-hfs-volume-name "klmat"'),
    ],
}


def apply_packaging_names() -> list:
    changed = []
    for rel, pairs in PACKAGING_NAMES.items():
        path = ROOT / rel
        src = path.read_text(encoding='utf-8')
        out = src
        for a, b in pairs:
            out = out.replace(a, b)
        if out != src:
            path.write_text(out, encoding='utf-8')
            changed.append(path)
    return changed


if __name__ == '__main__':
    main()
    for _p in apply_packaging_names():
        print('rebranded', _p.relative_to(ROOT))
