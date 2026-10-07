#!/bin/bash
# Tools for the flat-visualisation kit (macOS + Homebrew). Installs only what is missing; never upgrades what is already there.
#   bash tools.sh check     -> one line per tool (OK / MISSING), then the install plan; exit 1 if a required tool is missing
#   bash tools.sh install   -> runs that plan (brew), then checks again
BREW=$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1)
PLAN=()

check() {
  PLAN=(); local missing=0
  if command -v blender >/dev/null; then echo "OK       blender    $(blender --version 2>/dev/null | head -1)"
  elif [ -d /Applications/Blender.app ]; then missing=1; echo "MISSING  blender    app found, command not on PATH"
    if [ -n "$BREW" ]; then PLAN+=("ln -s /Applications/Blender.app/Contents/MacOS/Blender $(dirname "$BREW")/blender")
    else echo "NEEDS    run yourself: sudo ln -s /Applications/Blender.app/Contents/MacOS/Blender /usr/local/bin/blender"; fi
  else missing=1; echo "MISSING  blender"; PLAN+=("brew install --cask blender"); fi
  if command -v python3 >/dev/null; then echo "OK       python3    $(python3 --version 2>&1) ($(command -v python3))"
  else missing=1; echo "MISSING  python3"; PLAN+=("brew install python"); fi
  if python3 -c 'import PIL' 2>/dev/null; then echo "OK       pillow     $(python3 -c 'import PIL; print(PIL.__version__)')"
  else missing=1; echo "MISSING  pillow"
    case "$(command -v python3)" in
      ''|"$(dirname "${BREW:-/x/x}")"/*) PLAN+=("brew install pillow") ;;   # Homebrew python (pip is blocked there, PEP 668)
      *) PLAN+=("python3 -m pip install --user pillow") ;;                  # Apple's or another python
    esac; fi
  if command -v magick >/dev/null; then echo "OK       magick     $(magick -version | head -1 | cut -c1-40)"
  else missing=1; echo "MISSING  magick (ImageMagick)"; PLAN+=("brew install imagemagick"); fi
  if command -v pdftoppm >/dev/null; then echo "OK       pdftoppm   $(pdftoppm -v 2>&1 | head -1)"
  else missing=1; echo "MISSING  pdftoppm (poppler)"; PLAN+=("brew install poppler"); fi
  if [ -d "/Applications/Google Chrome.app" ]; then echo "OK       chrome     (optional: web light calibration)"
  else echo "OPTIONAL chrome     not found; only needed for render/web_floor.py"; fi
  if [ ${#PLAN[@]} -gt 0 ] && [ -z "$BREW" ] && printf '%s\n' "${PLAN[@]}" | grep -q '^brew'; then
    echo "NEEDS    Homebrew first (asks for your password, run it yourself):"
    echo '         /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  fi
  for c in "${PLAN[@]}"; do echo "PLAN     $c"; done
  [ $missing -eq 0 ] && echo "ALL REQUIRED TOOLS PRESENT"
  return $missing
}

case "$1" in
  check) check ;;
  install)
    check >/dev/null && { echo "nothing to install"; exit 0; }
    [ "$(uname)" = Darwin ] || { echo "install works on macOS only; install the MISSING tools by hand"; exit 2; }
    for c in "${PLAN[@]}"; do
      case "$c" in brew*) [ -n "$BREW" ] || { echo "Homebrew missing, see 'check'"; exit 2; }; c="$BREW${c#brew}" ;; esac
      echo ">> $c"; eval "$c" || { echo "FAILED: $c"; exit 1; }
    done
    hash -r; echo; check ;;
  *) echo "usage: bash tools.sh check | install"; exit 2 ;;
esac
