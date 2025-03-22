# -*- coding: utf-8 -*-
# Exibição de jogos na interface Kodi

# --- Modules/packages in this plugin ---
from .utils import *
from .steam import *
from .nonsteam import NonSteam

import os
import json
import requests
import subprocess
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from urllib.parse import parse_qsl, parse_qs, urlencode

class Main:    
    def __init__(self):
        # Inicializa as configurações e módulos
        self.settings = PluginSettings()
        self.non_steam = NonSteam() 
        self.steam_games_path = "special://userdata/addon_data/plugin.program.steamgames/steam_games.json"
        self.non_steam_games_path = "special://userdata/addon_data/plugin.program.steamgames/non_steam_games.json"
        self.json_dir = xbmcvfs.translatePath('special://userdata/addon_data/plugin.program.steamgames/')

    def run_plugin(self, args):
        """
        Ponto de entrada do plugin. Gerencia as ações baseadas nos argumentos.
        """
        params = parse_qs(args[2][1:]) if len(args) > 2 and "?" in args[2] else {}
        action = params.get('action', ['list'])[0]
        tag = params.get('tag', [None])[0]
        
        steam_games_json = os.path.join(self.json_dir, "steam_games.json")
        
        # Verifica se o JSON já existe
        if not xbmcvfs.exists(steam_games_json):
            self.sync_steam_games()
        
        if action == 'sync_steam_games':
            self.sync_steam_games()

        elif action == 'sync_nonsteam_games':
            self.non_steam.sync_non_steam_games()  # Chama a função de sincronização de jogos Non-Steam
            kodi_refresh_container()
        
        elif action == "play":
            appid = params.get('appid', [None])[0]
            if appid:
                self.play_game(appid)
            else:
                xbmcgui.Dialog().ok("Erro", "ID do jogo não encontrado.")
                
        elif action == "list_all_games":
            self.show_all_games()
        
        elif action == 'collections':
            self.saveShortcutsJson()
         
        elif action == 'settings':
            kodi_dialog_OK("Ajustes")
            xbmc.executebuiltin('Addon.OpenSettings({})'.format('plugin.program.steamgames'))
                       
        elif action == 'list_games_by_tag':
            if tag:
                self.show_games_by_tag(tag) 
        
        else:
            self.show_games_by_tags()                
             
    def show_all_games(self):
        """
        Lista todos os jogos Steam e Non-Steam em uma única tela.
        """
        steam_games = self.load_steam_games()  # Carrega jogos Steam
        nonsteam_games = self.load_non_steam_games()  # Carrega jogos Non-Steam

        # Combina as listas de jogos Steam e Non-Steam
        all_games = []

        if steam_games:
            all_games.extend([
                {
                    "appName": game.get("name", "Sem Nome"),
                    "appid": game.get("appid"),
                    "source": "Steam",
                    "icon": game.get("icon", ""),
                    "poster": game.get("capsule", ""),
                    "clearlogo": game.get("logo", ""),
                    "fanart": game.get("hero", ""),
                    "banner": game.get("hero", ""),
                    "tags": []
                } for game in steam_games
            ])

        if nonsteam_games:
            all_games.extend([
                {
                    "appName": game.get("appName", "Sem Nome"),
                    "appid": game.get("appid"),
                    "source": "Non-Steam",
                    "icon": game.get("icon", ""),
                    "poster": game.get("poster", ""),
                    "clearlogo": game.get("logo", ""),
                    "fanart": game.get("hero", ""),
                    "banner": None,
                    "tags": list(game.get("tags", {}).values())
                } for game in nonsteam_games
            ])

        # Ordena os jogos em ordem alfabética pelo nome
        all_games = sorted(all_games, key=lambda game: game["appName"].lower())

        # Renderiza cada jogo no Kodi
        for game in all_games:
            list_item = xbmcgui.ListItem(label=game["appName"])
            list_item.setArt({
                "icon": xbmcvfs.translatePath(game["icon"]),
                "poster": xbmcvfs.translatePath(game["poster"]),
                "clearlogo": xbmcvfs.translatePath(game["clearlogo"]),
                "fanart": xbmcvfs.translatePath(game["fanart"]),
                "banner": xbmcvfs.translatePath(game["banner"]) if game["banner"] else ""
            })
            
            list_item.setInfo("video", {
                "title": game["appName"],
                "genre": ", ".join(game["tags"]),
                "plot": f"Origem: {game['source']}"
            })
            
            # Adiciona o menu de contexto
            context_menu = [
                ("Atualizar Jogos Steam",       f"RunPlugin(plugin://plugin.program.steamgames?action=sync_steam_games)"),
                ("Atualizar Jogos Non-Steam",   f"RunPlugin(plugin://plugin.program.steamgames?action=sync_nonsteam_games)"),
                ("Atualizar Collections",       f"RunPlugin(plugin://plugin.program.steamgames?action=collections)"),
                ('Settings',                    f'RunPlugin(plugin://plugin.program.steamgames?action=settings)')
            ]
            list_item.addContextMenuItems(context_menu)

            # URL para executar o jogo
            url = f"plugin://plugin.program.steamgames/?action=play&appid={game['appid']}"
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url,
                listitem=list_item,
                isFolder=False
            )

        # Finaliza o diretório
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def load_non_steam_games(self):
        """
        Carrega os jogos Non-Steam do arquivo JSON.
        """
        nonsteam_games_json = xbmcvfs.translatePath(self.non_steam_games_path)
        if not xbmcvfs.exists(nonsteam_games_json):
            xbmcgui.Dialog().ok("Erro", "Nenhum jogo Non-Steam encontrado!")
            return []

        with open(nonsteam_games_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Acessa os jogos na chave "non_steam"
        return list(data.get("non_steam", {}).values())


    def load_steam_games(self):
        """
        Carrega os jogos Steam do arquivo JSON.
        """
        steam_games_json = xbmcvfs.translatePath(self.steam_games_path)
        if not xbmcvfs.exists(steam_games_json):
            xbmcgui.Dialog().ok("Erro", "Nenhum jogo Steam encontrado!")
            return []

        with open(steam_games_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Acessa os jogos na chave "steam"
        return list(data.get("steam", {}).values())
     
    def get_custom_art(self, path, folder_name, art_type):
        """
        Procura por uma imagem personalizada para a pasta.
        :param path: Caminho base para a pasta de arte.
        :param folder_name: Nome da pasta a ser renderizada.
        :param art_type: Tipo de arte (poster, icon, etc.).
        :return: Caminho completo para a imagem personalizada ou None.
        """
        if not path:
            return None
        file_name = f"{folder_name}.png"
        file_path = os.path.join(path, file_name)
        return file_path if os.path.exists(file_path) else None 
    
    def get_art_for_folder(self, folder_name):
        """
        Busca todas as artes disponíveis para uma pasta específica.
        :param folder_name: Nome da pasta.
        :return: Dicionário contendo os caminhos das artes.
        """
        # Caminhos obtidos do settings.xml
        poster_path = xbmcaddon.Addon().getSetting("poster_path")
        icons_path = xbmcaddon.Addon().getSetting("icons_path")
        banners_path = xbmcaddon.Addon().getSetting("banners_path")
        fanarts_path = xbmcaddon.Addon().getSetting("fanarts_path")
        clearlogos_path = xbmcaddon.Addon().getSetting("clearlogos_path")

        # Coleta as artes personalizadas
        return {
            "poster": self.get_custom_art(poster_path, folder_name, "poster") or "DefaultFolder.png",
            "icon": self.get_custom_art(icons_path, folder_name, "icon") or "DefaultFolder.png",
            "banner": self.get_custom_art(banners_path, folder_name, "banner") or "DefaultFolder.png",
            "fanart": self.get_custom_art(fanarts_path, folder_name, "fanart") or "DefaultFanart.png",
            "clearlogo": self.get_custom_art(clearlogos_path, folder_name, "clearlogo") or ""
        }
    
    def sync_steam_games(self):
        """
        Chama a sincronização de jogos da Steam.
        """
        
        # Instancia a classe SteamAPI e tenta buscar os jogos
        steam_api = SteamAPI(self.settings.steam_user_id, self.settings.steam_api_key)
        games = steam_api.get_owned_games()

        if games:
            # Se os jogos forem obtidos, instanciar o GameSaver e salvar
            game_saver = GameSaver()
            game_saver.save_games(games)
             
    def show_games_by_tags(self):
        """
        Exibe os jogos Steam e Non-Steam em pastas unificadas por tags na interface Kodi.
        """
        steam_games = self.load_steam_games()
        non_steam_games = self.load_non_steam_games()

        # Agrupamento por tags
        grouped_games = {}
        uncategorized_games = []  # Jogos sem tags

        # Agrupa jogos Steam
        for game in steam_games:
            # tags = game.get("tags", {}).values()
            tags = game.get("tags", {})
            if not tags:
                uncategorized_games.append(game)
            else:
                for tag_name in tags:
                    if tag_name not in grouped_games:
                        grouped_games[tag_name] = []
                    grouped_games[tag_name].append(game)

        # Agrupa jogos Non-Steam
        for game in non_steam_games:
            # tags = game.get("tags", {}).values()
            tags = game.get("tags", {})
            if not tags:
                uncategorized_games.append(game)
            else:
                for tag_name in tags:
                    if tag_name not in grouped_games:
                        grouped_games[tag_name] = []
                    grouped_games[tag_name].append(game)

        # Criar pastas para cada tag
        for tag_name, games in sorted(grouped_games.items()):
            arts = self.get_art_for_folder(tag_name)
            tag_item = xbmcgui.ListItem(label=tag_name)
            tag_item.setArt(arts)
            tag_item.setInfo("video", {"title": tag_name, "genre": "Jogos"})

            # Adicionar menu de contexto à pasta
            context_menu = [
                ("Atualizar Jogos Steam",       f"RunPlugin(plugin://plugin.program.steamgames?action=sync_steam_games)"),
                ("Atualizar Jogos Non-Steam",   f"RunPlugin(plugin://plugin.program.steamgames?action=sync_nonsteam_games)"),
                ("Atualizar Collections",       f"RunPlugin(plugin://plugin.program.steamgames?action=collections)"),
                ('Settings',                    f'RunPlugin(plugin://plugin.program.steamgames?action=settings)')
            ]
            tag_item.addContextMenuItems(context_menu)

            # URL para abrir a pasta de jogos com esta tag
            tag_url = f"plugin://plugin.program.steamgames/?action=list_games_by_tag&tag={tag_name}"
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=tag_url,
                listitem=tag_item,
                isFolder=True
            )

        # Adicionar a pasta "Steam", se houver jogos sem tags
        if uncategorized_games:
            folder_name = "Steam"
            arts = self.get_art_for_folder(folder_name)
            uncategorized_item = xbmcgui.ListItem(label=folder_name)
            uncategorized_item.setArt(arts)
            uncategorized_item.setInfo("video", {"title": folder_name, "genre": "Jogos"})

            # Adicionar menu de contexto à pasta
            context_menu = [
                ("Atualizar Jogos Steam",       f"RunPlugin(plugin://plugin.program.steamgames?action=sync_steam_games)"),
                ("Atualizar Jogos Non-Steam",   f"RunPlugin(plugin://plugin.program.steamgames?action=sync_nonsteam_games)"),
                ("Atualizar Collections",       f"RunPlugin(plugin://plugin.program.steamgames?action=collections)"),
                ('Settings',                    f'RunPlugin(plugin://plugin.program.steamgames?action=settings)')
            ]
            uncategorized_item.addContextMenuItems(context_menu)

            uncategorized_url = "plugin://plugin.program.steamgames/?action=list_games_by_tag&tag=uncategorized"
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=uncategorized_url,
                listitem=uncategorized_item,
                isFolder=True
            )

        # Finaliza o diretório
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def show_games_by_tag(self, tag):
        """
        Lista os jogos Steam e Non-Steam de uma tag específica.
        """
        steam_games = self.load_steam_games()
        non_steam_games = self.load_non_steam_games()

        # Filtra jogos pela tag ou sem categoria
        if tag == "uncategorized":
            filtered_games = [
                *[game for game in steam_games if not game.get("tags")],
                *[game for game in non_steam_games if not game.get("tags")]
            ]
        else:
            filtered_games = [
                *[game for game in steam_games if tag in (game.get("tags", {}).values() if isinstance(game.get("tags"), dict) else [game.get("tags")])],
                *[game for game in non_steam_games if tag in (game.get("tags", {}).values() if isinstance(game.get("tags"), dict) else [game.get("tags")])]
            ]

        # Ordena os jogos em ordem alfabética pelo nome
        filtered_games = sorted(filtered_games, key=lambda game: game.get("appName", "").lower())

        for game in filtered_games:
            list_item = xbmcgui.ListItem(label=game.get("appName", "Sem Nome"))
            list_item.setArt({
                "icon": xbmcvfs.translatePath(game.get("icon", "")),
                "poster": xbmcvfs.translatePath(game.get("capsule", "")),
                "clearlogo": xbmcvfs.translatePath(game.get("logo", "")),
                "fanart": xbmcvfs.translatePath(game.get("hero", "")),
            })
            list_item.setInfo("video", {
                "title": game.get("appName", "Sem Nome"),
                "genre": ", ".join(game.get('tags', {}).values() if isinstance(game.get("tags"), dict) else [game.get("tags")]),
                "plot": f"Último acesso: {game.get('LastPlayTime', 0)}"
            })
            
            # Adicionar menu de contexto à pasta
            context_menu = [
                ("Atualizar Jogos Steam",       f"RunPlugin(plugin://plugin.program.steamgames?action=sync_steam_games)"),
                ("Atualizar Jogos Non-Steam",   f"RunPlugin(plugin://plugin.program.steamgames?action=sync_nonsteam_games)"),
                ("Atualizar Collections",       f"RunPlugin(plugin://plugin.program.steamgames?action=collections)"),
                ('Settings',                    f'RunPlugin(plugin://plugin.program.steamgames?action=settings)')
            ]
            list_item.addContextMenuItems(context_menu)

            # URL para executar o jogo
            url = f"plugin://plugin.program.steamgames/?action=play&appid={game['appid']}"
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url,
                listitem=list_item,
                isFolder=False
            )

        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def saveShortcutsJson(self):
        """
        Executa o arquivo .exe localizado na pasta resources/vdf e aguarda sua conclusão.
        Permite editar as tags de múltiplos itens no JSON simultaneamente.
        Se nenhum item for selecionado, executa outro arquivo .exe.
        """
        
        self.addon = xbmcaddon.Addon(id='plugin.program.steamgames')
        self.shortcuts_path = self.addon.getSetting('shortcuts_path')

        # Caminho completo para o executável e diretório de destino
        addon_path = xbmcaddon.Addon().getAddonInfo('path')
        json_exe = os.path.join(addon_path, 'resources', 'vdf', 'saveShortcutsJson.exe')
        vdf_exe = os.path.join(addon_path, 'resources', 'vdf', 'saveShortcutsVdf.exe')
        dir_path = os.path.join(addon_path, 'resources', 'vdf')
        json_path = os.path.join(dir_path, 'shortcuts.json')
        
        if not os.path.exists(json_exe):
            kodi_notify_error(f"Executável não encontrado: {json_exe}")
            return

        try:
            # Mostra o diálogo de progresso
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create("Steam Games", "Aguarde enquanto listamos as Coleções")

            # Executa o arquivo e aguarda sua conclusão
            process = subprocess.Popen(
                [json_exe, dir_path],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            while process.poll() is None:
                if progress_dialog.iscanceled():
                    process.terminate()
                    kodi_notify_warn("Steam Games", "Processo interrompido pelo usuário.")
                    return
                xbmc.sleep(100)  # Aguarda 100ms antes de verificar novamente

            # Lê a saída e o erro
            stdout, stderr = process.communicate()
            if stdout:
                kodi_log(f"STDOUT: {stdout}")
            if stderr:
                kodi_log(f"STDERR: {stderr}")

            # Fecha o diálogo de progresso
            progress_dialog.close()

            # Exibe a notificação de sucesso
            kodi_notify("Coleções Processadas!")

            # Ler o arquivo JSON em loop
            while True:
                if not os.path.exists(json_path):
                    kodi_notify_warn(f"Arquivo de Coleção não encontrado: {json_path}")
                    return

                with open(json_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                # Montar a lista de opções (nome: tags)
                options = [f"{name}: {', '.join(tags)}" for name, tags in data.items()]
                selected = xbmcgui.Dialog().multiselect("Selecione os jogos para editar a coleção", options)
                
                # Verificar se o usuário clicou em "Cancelar"
                if selected is None:
                    return  # Sai da função sem executar nada
                
                if not selected:
                    # Se nada for selecionado, executa outro arquivo .exe
                    kodi_notify("Coleções Atualizadas com sucesso!")
                    
                    # Executa o arquivo e aguarda sua conclusão
                    process = subprocess.Popen([vdf_exe, dir_path], shell=True)

                    while process.poll() is None:
                        if progress_dialog.iscanceled():
                            process.terminate()
                            kodi_notify_warn("Processo interrompido pelo usuário.")
                            return
                        xbmc.sleep(100)  # Aguarda 100ms antes de verificar novamente
                        
                    xbmc.sleep(500)
                    
                    # Copiar o arquivo shortcuts_updated.vdf da pasta "dir_path" para a pasta "self.shortcuts_path", renomeando para shortcuts.vdf, sobrepondo o antigo
                    updated_vdf_path = os.path.join(dir_path, 'shortcuts_updated.vdf')
                    destination_path = os.path.join(self.shortcuts_path, 'shortcuts.vdf')

                    if os.path.exists(updated_vdf_path):
                        try:
                            shutil.copy(updated_vdf_path, destination_path)  # Copia o arquivo e sobrescreve o destino
                            kodi_log("Arquivo shortcuts.vdf atualizado com sucesso!")
                        
                        except Exception as e:
                            kodi_notify(f"Falha ao copiar o arquivo: {str(e)}")
                            kodi_log(f"Falha ao copiar o arquivo: {str(e)}")
                    else:
                        kodi_notify_warn("Arquivo shortcuts_updated.vdf não encontrado!")
                        kodi_log("Arquivo shortcuts_updated.vdf não encontrado!")
                    
                    self.non_steam.sync_non_steam_games()  # Chama a função de sincronização de jogos Non-Steam
                    kodi_refresh_container()

                    return

                # Obter os jogos selecionados
                selected_games = [list(data.keys())[i] for i in selected]
                selected_tags = [data[game] for game in selected_games]

                # Criar uma lista de tags para editar
                combined_tags = list(set(tag for tags in selected_tags for tag in tags))

                # Mostrar para o usuário as tags atuais para todos os jogos selecionados
                new_tags = xbmcgui.Dialog().input(
                    f"Editar tags para os jogos selecionados: {', '.join(selected_games)}",
                    defaultt=", ".join(combined_tags),
                    type=xbmcgui.INPUT_ALPHANUM
                )

                if new_tags is not None:
                    # Separar as tags por vírgula e atualizar todos os jogos selecionados
                    new_tags_list = [tag.strip() for tag in new_tags.split(',')]

                    # Atualizar os jogos selecionados
                    for game in selected_games:
                        data[game] = new_tags_list

                    # Salvar o arquivo atualizado
                    with open(json_path, 'w', encoding='utf-8') as file:
                        json.dump(data, file, ensure_ascii=False, indent=2)

                    kodi_notify("Coleções para os jogos selecionados foram atualizados!")
                    
        except Exception as e:
            # Fecha o diálogo de progresso em caso de erro
            if 'progress_dialog' in locals():
                progress_dialog.close()
                
            kodi_notify(f"Falha ao executar o arquivo: {str(e)}")
    
    def play_game(self, appid):
        """
        Simula a execução de um jogo com base no appid.
        """
        try:
            # Comando para executar o Steam com o appid
            steam_command = f'steam.exe steam://rungameid/{appid}'

            # Executa o comando
            kodi_log(f"Executando: {steam_command}")
            subprocess.run(steam_command, shell=True, cwd="C:\\Program Files (x86)\\Steam")

            # Notifica o usuário sobre o início do jogo
            # kodi_dialog_OK("Iniciar Jogo", f"Iniciando o jogo com ID: {appid}")
        except Exception as e:
            # Tratamento de erros e exibição de mensagem
            kodi_dialog_OK(f"Não foi possível iniciar o jogo. Detalhes: {str(e)}")
    