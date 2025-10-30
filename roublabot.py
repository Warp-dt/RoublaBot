import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv

# LOAD OUR TOKEN FROM .env
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

MEMBER_ROLE_ID= 1201113600518017064 #à modifier avec l'identifiant du role que le bot doit donner
# MEMBER_ROLE_ID = 1201113600518017064 #à modifier avec l'identifiant du role que le bot doit donner

# Liste des serveurs disponibles
SERVERS = ["Brial","Dakal","Draconiros","Hell Mina","Imagiro","Kourial","Ombre","Orukam","Rafal","Salar","Tal Kasha","Tylezia"
           ,"Touch/Kelerog","Touch/Tiliwan","Touch/Blair","Touch/Talok","Retro/Allisteria","Retro/Boune","Retro/Fallanster"]
MAX_NICKNAME_LENGTH = 32
CONFIG_FILE = "bot_config.json"

class WelcomeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.welcome_channels = {}
        self.load_config()
        
    async def setup_hook(self):
        await self.tree.sync()
    
    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.welcome_channels = json.load(f)
        except FileNotFoundError:
            self.welcome_channels = {}
    
    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.welcome_channels, f)

bot = WelcomeBot()

class RegisterButton(discord.ui.Button):
    def __init__(self, target_user_id: int):
        super().__init__(label="S'identifier", style=discord.ButtonStyle.primary)
        self.target_user_id = target_user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.target_user_id:
            modal = RegistrationModal()
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "🚫 Ce bouton est réservé à l’utilisateur concerné.",
                ephemeral=True
            )

class RegistrationModal(discord.ui.Modal, title="Identification"):
    character_name = discord.ui.TextInput(
        label="Nom du personnage",
        placeholder="Entrez votre nom de personnage",
        min_length=2,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Vérifie si le nom contient un chiffre
        if any(char.isdigit() for char in self.character_name.value):
            view = discord.ui.View()
            view.add_item(RegisterButton(interaction.user.id))

            await interaction.response.send_message(
                "❌ Le nom de personnage ne doit pas contenir de chiffres.\n"
                "Veuillez entrer un nom valide puis cliquez sur le bouton ci-dessous pour recommencer :",
                view=view,
                ephemeral=True
            )
            return

        
        # Si le nom est valide, passe à la sélection du serveur
        view = discord.ui.View()
        view.add_item(ServerSelect(self.character_name.value))
        await interaction.response.send_message(
            f"Nom choisi : {self.character_name.value}\n**Choisissez votre serveur :**", 
            view=view,
            ephemeral=True
        )

class ServerSelect(discord.ui.Select):
    def __init__(self, character_name):
        self.character_name = character_name
        options = [
            discord.SelectOption(label=server, value=server)
            for server in SERVERS
        ]
        super().__init__(
            placeholder="Choisissez votre serveur",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        server = self.values[0]
        new_nickname = f"{self.character_name} [{server}]"
        
        if len(new_nickname) > MAX_NICKNAME_LENGTH:
            await interaction.response.send_message(
                f"❌ Le pseudo '{new_nickname}' est trop long "
                f"({len(new_nickname)}/{MAX_NICKNAME_LENGTH} caractères).",
                ephemeral=True
            )
            return
        
        try:
            guild_member = interaction.guild.get_member(interaction.user.id)
            await guild_member.edit(nick=new_nickname)
            
            # Attribution du rôle après le changement de pseudo réussi
            role = interaction.guild.get_role(MEMBER_ROLE_ID)
            if role:
                await guild_member.add_roles(role)
                await interaction.response.edit_message(
                    content=f"✅ Votre pseudo a été mis à jour en : **{new_nickname}**\n"
                            f"Le rôle *{role.name}* vous a été attribué.",
                    view=None
                )
            else:
                await interaction.response.edit_message(
                    content=f"✅ Votre pseudo a été mis à jour en : **{new_nickname}**\n"
                            f"(⚠️ Rôle introuvable)",
                    view=None
                )
                
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Je n'ai pas les permissions nécessaires pour changer votre pseudo ou attribuer le rôle.",
                ephemeral=True               
            )
        except AttributeError:
            await interaction.response.send_message(
                "❌ Une erreur s'est produite. Vérifiez mes permissions.",
                ephemeral=True
            )

@bot.event
async def on_member_join(member):
    # Utilise le canal configuré ou par défaut le canal système
    channel_id = bot.welcome_channels.get(str(member.guild.id))
    channel = member.guild.get_channel(int(channel_id)) if channel_id else None

    if not channel:
        channel = member.guild.system_channel or member.guild.text_channels[0]
    
    if channel:
        view = discord.ui.View()
        view.add_item(RegisterButton(member.id))

        await channel.send(
            f"👋 Bienvenue {member.mention} !\n"
            f"Clique sur le bouton ci-dessous pour t'identifier :",
            view=view
        )        

@bot.tree.command(name="identification", description="Lance le processus d'identification")
async def identification(interaction: discord.Interaction):
    modal = RegistrationModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(
    name="definir_canal_identification",
    description="Définit le canal pour les messages d'identification'"
)
@app_commands.default_permissions(administrator=True)
async def definir_canal_identification(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.welcome_channels[str(interaction.guild.id)] = channel.id
    bot.save_config()
    await interaction.response.send_message(
        f"Le canal des messages d'identification a été défini sur {channel.mention}",
        ephemeral=True
    )

@bot.tree.command(
    name="voir_canal_identification",
    description="Affiche le canal actuel des messages d'identification'"
)
@app_commands.default_permissions(administrator=True)
async def voir_canal_identification(interaction: discord.Interaction):
    channel_id = bot.welcome_channels.get(str(interaction.guild.id))
    if channel_id:
        channel = interaction.guild.get_channel(int(channel_id))
        if channel:
            await interaction.response.send_message(
                f"Le canal actuel des messages d'identification est {channel.mention}",
                ephemeral=True
            )
            return
    
    await interaction.response.send_message(
        "Aucun canal d'identification n'est configuré. Le canal système sera utilisé par défaut.",
        ephemeral=True
    )


bot.run(BOT_TOKEN)