#!/bin/bash
# SwiftRDP.sh – Vérifie les dépendances, corrige le fichier desktop et lance l'application SwiftRDP

# --- Vérification des dépendances ---
if ! command -v zenity >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y zenity || exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    if zenity --question --title="Dépendance manquante" --text="python3 n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y python3 || exit 1
    else
        zenity --error --text="python3 est requis. Arrêt." --width=300
        exit 1
    fi
fi

if ! command -v pip3 >/dev/null 2>&1; then
    if zenity --question --title="Dépendance manquante" --text="pip3 n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y python3-pip || exit 1
    else
        zenity --error --text="pip3 est requis. Arrêt." --width=300
        exit 1
    fi
fi

python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    if zenity --question --title="Dépendance manquante" --text="Tkinter n'est pas disponible. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y python3-tk || exit 1
    else
        zenity --error --text="Tkinter est requis. Arrêt." --width=300
        exit 1
    fi
fi

if ! command -v xfreerdp >/dev/null 2>&1; then
    sess_type=$(echo "$XDG_SESSION_TYPE")
    if [ "$sess_type" = "wayland" ]; then
        pkg="freerdp2-wayland"
    else
        pkg="freerdp2-x11"
    fi
    if zenity --question --title="Dépendance manquante" --text="Le paquet pour SwiftRDP n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y "$pkg" || exit 1
    else
        zenity --error --text="Le paquet SwiftRDP est requis. Arrêt." --width=300
        exit 1
    fi
fi

if ! command -v wmctrl >/dev/null 2>&1; then
    if zenity --question --title="Dépendance manquante" --text="wmctrl n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y wmctrl || exit 1
    else
        zenity --error --text="wmctrl est requis. Arrêt." --width=300
        exit 1
    fi
fi

if ! command -v git >/dev/null 2>&1; then
    if zenity --question --title="Dépendance manquante" --text="git n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt-get update && sudo apt install -y git || exit 1
    else
        zenity --error --text="git est requis. Arrêt." --width=300
        exit 1
    fi
fi

# --- Vérifier et corriger le fichier desktop ---
DESKTOP_FILE="/usr/share/applications/SwiftRDP.desktop"
REQUIRED_EXEC="Exec=/opt/SwiftRDP/SwiftRDP.sh %u"
REQUIRED_MIME="MimeType=x-scheme-handler/rdp;"
if [ -f "$DESKTOP_FILE" ]; then
    sudo sed -i "s|^Exec=.*|$REQUIRED_EXEC|" "$DESKTOP_FILE"
    if grep -q "^MimeType=" "$DESKTOP_FILE"; then
        sudo sed -i "s|^MimeType=.*|$REQUIRED_MIME|" "$DESKTOP_FILE"
    else
        echo "$REQUIRED_MIME" | sudo tee -a "$DESKTOP_FILE" >/dev/null
    fi
    sudo update-desktop-database /usr/share/applications/
fi

# --- Lancer l'application Python en transmettant les arguments (y compris les liens rdp://)
python3 /opt/SwiftRDP/SwiftRDP_app.py "$@"
