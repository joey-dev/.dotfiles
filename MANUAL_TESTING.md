# Manual Testing Guide

Some features cannot be easily tested in an automated virtual machine.

This is usually because they require real physical hardware, specific external network conditions, or complex human interactions.

This document lists what you need to check manually when you are doing a big update.

## Physical Hardware & Keys

Because a virtual machine does not have a real screen backlight or speakers, these tests must be done on your real laptop.

### Brightness

**How to test:**
- Press the `Brightness Up` key on your keyboard.
- Verify that the screen actually gets brighter.
- Press the `Brightness Down` key.
- Verify that the screen actually gets darker.
- Make sure a notification or on-screen display shows the change.

### Audio

**How to test:**
- Play a YouTube video or a sound file.
- Press the `Volume Up` and `Volume Down` keys on your keyboard.
- Verify that the sound changes.
- Press the `Mute` key and verify the sound stops completely.
- Open `pulsemixer` or `pavucontrol` and check if the audio devices are detected.

### Multiple Monitors (Autorandr)

**How to test:**
- Plug in an external monitor.
- Press `Super+m` (Mod+m) to load your autorandr monitor layout profiles.
- Verify that the screen extends properly.
- Try switching workspaces across monitors using `Super+Shift+d`.

### Power Settings (xidlehook & LightDM)

**How to test:**
- Leave your laptop untouched for the configured auto-lock time.
- Verify that the screen locks automatically.
- Try suspending the laptop (closing the lid).
- Open the lid and verify that the LightDM login screen wakes up correctly.
- Check the power menu (`Super+p`) and make sure the shutdown and restart options work.

## External Services & Networking

Some tools rely on external websites or private networks.

### SSH & Git

**How to test:**
- Run a `git fetch` in a repository that uses an SSH key.
- Verify that the SSH agent prompts you for the password if needed, or works seamlessly.
- Check if you can connect to your private hosts in `~/.ssh/config.local`.

### Database Connectivity (DBeaver)

**How to test:**
- Open DBeaver.
- Try to connect to a local PostgreSQL or MySQL database if you have one running.
- Use `Ctrl+d` to view data in a table.
- Verify that the imported general preferences and shortcuts are still active.

## Complex UI Interactions

While we can test if an app opens, checking if it *looks* perfect is very hard for a machine.

### GTK Theme & Fonts

**How to test:**
- Open a GTK application like a file manager.
- Verify that the colors match your expected GTK theme.
- Open your terminal (Alacritty or Ghostty).
- Check that the `ComicShannsMono` Nerd Font is being used.
- Make sure that icons in your terminal and status bar (`polybar`) are rendering correctly, without missing squares.
