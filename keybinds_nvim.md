# Neovim Keybindings

## Git
- Open Git Status: `<leader>gs`
  - Add all files: `A`
  - Unstage file: `gu`
  - Add file: `ga`
  - Revert file: `gr`
  - Commit: `gc`
  - Push: `gp`
  - Commit and Push: `gg`

## Project Tree (pf)
- Open Tree: `<leader>pf`
- Open Tree and focus on the current open file: `<leader>pcf`
- Open Tree with only open files: `<leader>pof`

  - Within Open Files (pof):
    - Delete Buffer: `bd`

  - Within Project Tree (pf):
    - Fuzzy Finder: `/`
    - Fuzzy Finder for Directories: `D`
    - Navigate Up: `<bs>`
    - Open Split: `S`
    - Open Vertical Split: `s`
    - Close Node: `C`
    - Close All Nodes: `z`
    - Add File or Directory: `a`
    - Add Directory: `A` (also accepts optional config.show_path option like "add")
    - Delete: `d`
    - Rename: `r`
    - Copy to Clipboard: `y`
    - Cut to Clipboard: `x`
    - Paste from Clipboard: `p`
    - Copy (text input for destination): `c` (also accepts optional config.show_path option like "add")
    - Move (text input for destination): `m` (also accepts optional config.show_path option like "add")

## Project Management (pl)
- List all projects: `<leader>pl`

## File Search
- Find text in all files in the current project: `<leader>fif`
- Find a file in the current project: `<leader>ff`

## Task Management (tm)
- Find/Run all tasks in the current project: `<leader>tm`

## Markdown Viewing
- View Markdown: `<leader>vm`
- Stop viewing Markdown: `<leader>vM`

## Marked Files
- Set mark on file: `<leader>mf`
- Clear mark list: `<leader>mc`
- Remove mark from file: `<leader>mr`
- Show all marked files: `<leader>M`
- Go to next marked file: `<leader>me`
- Go to previous marked file: `<leader>mq`

## Navigation
- Go back 1 file: `Alt + q`
- Go to next file: `Alt + e`
