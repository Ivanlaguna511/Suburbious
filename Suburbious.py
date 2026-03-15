""" 
Authors: Iván Moro Cienfuegos and Daniel Viñas Vega 
Refactored, commented, and translated for professional portfolio.
"""

from enum import IntEnum
from random import choice
import wx
import wx.adv
import random
import os

class ElementType(IntEnum):
    """ Enumeration defining all possible element types on the board """
    EMPTY = 0
    STORE = 1
    HOUSE = 2
    MANSION = 3
    BUILDING = 4
    HOSPITAL = 5
    BIGFOOT = 6
    BABY = 7
    SCHOOL = 8
    UNIVERSITY = 9
    WICK = 10
    RUBBLE = 11

class ElementInfo(object):
    """ Groups the static information and properties about an element type """
    def __init__(self, char, board_freq, game_freq, points, collapse_target):
        self.char = char                  # Console character representation
        self.board_freq = board_freq      # Spawn frequency on initial board
        self.game_freq = game_freq        # Spawn frequency during gameplay
        self.points = points              # Points awarded
        self.collapse_target = collapse_target  # Element it upgrades to upon matching 3

class Element(object):
    """ 
    Represents an element in a specific cell.
    Contains the element type and its age (used for Bigfoot mechanics).
    """
    
    # Information table mapping ElementTypes to their respective properties
    TABLE = {
        ElementType.EMPTY: ElementInfo('.', 45, 0, 0, None),
        ElementType.STORE: ElementInfo('a', 18, 60, 1, ElementType.HOUSE),
        ElementType.HOUSE: ElementInfo('b', 4, 10, 5, ElementType.MANSION),
        ElementType.MANSION: ElementInfo('c', 3, 2, 25, ElementType.BUILDING),
        ElementType.BUILDING: ElementInfo('d', 0, 0, 125, ElementType.HOSPITAL),
        ElementType.HOSPITAL: ElementInfo('e', 0, 0, 625, None),
        ElementType.BIGFOOT: ElementInfo('1', 2, 12, -25, None),
        ElementType.BABY: ElementInfo('2', 0, 0, -5, ElementType.SCHOOL),
        ElementType.SCHOOL: ElementInfo('3', 0, 0, 50, ElementType.UNIVERSITY),
        ElementType.UNIVERSITY: ElementInfo('4', 0, 0, 500, None),
        ElementType.WICK: ElementInfo('W', 0, 1, 0, None),
        ElementType.RUBBLE: ElementInfo('X', 0, 0, -50, None)
    }

    def __init__(self, elem_type, age=0):
        self.type = elem_type
        self.age = age

    def inc_age(self):
        """ Increments the element's age """
        self.age += 1

    @property
    def char(self):
        """ Returns the character associated with this element """
        return Element.TABLE[self.type].char

    @property
    def points(self):
        """ Returns the score of this element """
        return Element.TABLE[self.type].points

# --- REFACTOR: UI HELPER FUNCTION ---
def get_image_path(elem_type, age=0):
    """ 
    Maps an ElementType to its physical image path.
    Replaces hundreds of repetitive IF statements in the UI setup.
    """
    paths = {
        ElementType.EMPTY: ".\\Vacio.jpg",
        ElementType.STORE: ".\\Tienda.jpg",
        ElementType.HOUSE: ".\\Casa.jpg",
        ElementType.MANSION: ".\\Mansion.jpg",
        ElementType.BUILDING: ".\\Edificio.jpg",
        ElementType.HOSPITAL: ".\\Hospital.jpg",
        ElementType.BABY: ".\\Bebe.jpg",
        ElementType.SCHOOL: ".\\Escuela.jpg",
        ElementType.UNIVERSITY: ".\\Universidad.jpg",
        ElementType.WICK: ".\\Wick.jpg",
        ElementType.RUBBLE: ".\\Escombro.jpg"
    }
    
    # Handle dynamic Bigfoot textures based on age
    if elem_type == ElementType.BIGFOOT:
        if age >= 10: return ".\\Bigfoot10.jpg"
        if age >= 5: return ".\\Bigfoot5.jpg"
        return ".\\Bigfoot.jpg"
        
    return paths.get(elem_type, ".\\Vacio.jpg")

class Game(object):
    """ Represents the core game state and board logic """

    # --- GAME CONSTANTS ---
    NUM_ROWS = 6  
    NUM_COLS = 6  
    COLLAPSE_SIZE = 3  
    RUBBLE_AGE = 10  
    NEIGHBORS = [(-1, 0), (0, 1), (1, 0), (0, -1)]  # Directions for adjacent cells
    
    # State flags
    read_file = False
    create_random = False
    create_custom_size = False
    file_path = "x.txt"

    def __init__(self):
        self.sound_collapse = wx.adv.Sound(".\\colapso.wav")
        self.sound_oof = wx.adv.Sound(".\\oof.wav")

        # Create arrays for random drawing based on frequencies
        self.random_board_pool = [t for elem_type in ElementType for t in [elem_type] * Element.TABLE[elem_type].board_freq]
        self.random_seq_pool = [t for elem_type in ElementType for t in [elem_type] * Element.TABLE[elem_type].game_freq]
        
        self.sequence = []
        self.board = None
        
        if self.read_file:
            self.load_file(self.file_path)
   
        if self.create_random or self.create_custom_size:
            self.create_random_board()

        self.turn = 1
        self.score = self.calculate_score()
        self.storage = Element(ElementType.EMPTY)
        self.current = self.choose_current()

    def __getitem__(self, pos):
        """ Matrix notation getter: game[i,j] """
        return self.board[pos[0]][pos[1]]

    def __setitem__(self, pos, value):
        """ Matrix notation setter: game[i,j] = value """
        self.board[pos[0]][pos[1]] = value

    @property
    def bigfoots(self):
        """ Generator yielding coordinates and elements of all bigfoots """
        nrows, ncols = len(self.board), len(self.board[0])
        for i in range(nrows):
            for j in range(ncols):
                if self.board[i][j].type == ElementType.BIGFOOT:
                    yield i, j, self.board[i][j]

    def load_file(self, filename):
        """ Loads the element sequence and the board layout from a file """
        char_type = dict((Element.TABLE[elem_type].char, elem_type) for elem_type in ElementType)
        with open(filename) as f:
            self.sequence = [char_type[char] for char in f.readline().strip()]

        with open(filename) as f:
            next(f)  # Skip the first line
            self.board = [[Element(char_type[char]) for char in line] for line in f.read().splitlines()] 

    def create_random_board(self):
        """ Populates a board of NUM_ROWS x NUM_COLS with random elements """
        self.board = [[Element(choice(self.random_board_pool)) for _ in range(self.NUM_COLS)] for _ in range(self.NUM_ROWS)]

    def choose_current(self):
        """ Chooses the next element from the sequence or randomly """
        if self.sequence:
            self.sequence = self.sequence[1:] + [self.sequence[0]]
            return Element(self.sequence[-1])
        else:
            return Element(choice(self.random_seq_pool))

    def calculate_score(self):
        """ Calculates current score by summing points of all elements """
        return sum(elem.points for row in self.board for elem in row)

    def in_bounds(self, row, col):
        """ Checks if coordinates are within the board limits """
        return 0 <= row < len(self.board) and 0 <= col < len(self.board[0])

    def swap_storage(self):
        """ Swaps the storage element with the current one """
        self.current, self.storage = self.storage, self.current
        if self.current.type == ElementType.EMPTY:
            self.current = self.choose_current() 

    def play_turn(self, row, col):
        """ 
        Executes a move and triggers subsequent board reactions.
        Returns True if the game is over (board is full).
        """
        PlayBoard.play_sound = True
        
        # Step 1: Place element or use Wick
        if self.current.type == ElementType.WICK:
            self[row, col] = Element(ElementType.EMPTY)
        else:
            self[row, col] = self.current
            # Step 2: Trigger Match-3 Collapses
            while self.trigger_collapse(row, col):
                pass
                
        # Step 3: Bigfoot logic
        self.inc_bigfoot_age()
        babies = self.trap_bigfoots()
        if len(babies) > 0:
            self.collapse_babies(babies)
            
        self.move_bigfoots()
        
        # Update turn states
        self.turn += 1
        self.current = self.choose_current()
        self.score = self.calculate_score()
        
        return all(e.type != ElementType.EMPTY for row in self.board for e in row)
            
    def trigger_collapse(self, row, col):
        """ Checks for adjacent elements and upgrades them if 3+ are connected """
        elem = self[row, col]
        collapse_type = Element.TABLE[elem.type].collapse_target  
        
        if collapse_type is None:
            return False
            
        group = self.calc_group(row, col, lambda e: e.type == elem.type)
        if len(group) >= self.COLLAPSE_SIZE:
            for i, j in group:
                self[i, j] = Element(ElementType.EMPTY)
            self[row, col] = Element(collapse_type)
            
            self.sound_collapse.Play(wx.adv.SOUND_SYNC)
            PlayBoard.play_sound = False
            return True
        return False

    def inc_bigfoot_age(self):
        for _, _, e in self.bigfoots:
            e.inc_age()

    def trap_bigfoots(self):
        """ Converts enclosed Bigfoots into Babies """
        babies = set()
        for row, col, elem in self.bigfoots:
            region = self.calc_group(row, col, lambda e: e.type == ElementType.EMPTY or e.type == ElementType.BIGFOOT)
            
            if all(self[i, j].type != ElementType.EMPTY for i, j in region):
                babies |= region  
                for pos in region:
                    self[pos] = Element(ElementType.BABY, self[pos].age)  
                    self.sound_oof.Play(wx.adv.SOUND_SYNC)
        return babies

    def collapse_babies(self, babies):
        while len(babies) > 0:
            row, col = babies.pop()
            group = self.calc_group(row, col, lambda e: e.type == ElementType.BABY)
            babies -= group  
            if len(group) >= Game.COLLAPSE_SIZE:
                _, r, c = max(((self[i, j].age, i, j) for i, j in group), key=lambda t: t[0])
                while self.trigger_collapse(r, c):
                    pass

    def move_bigfoots(self):
        """ Moves Bigfoots to adjacent empty spaces or turns them to Rubble if too old """
        bigfoots = sorted(list(self.bigfoots), key=lambda t: t[2].age, reverse=True)
        for i, j, elem in bigfoots:
            for di, dj in Game.NEIGHBORS:
                mi, mj = i+di, j+dj
                if self.in_bounds(mi, mj) and self[mi, mj].type == ElementType.EMPTY:
                    self[mi, mj] = elem
                    self[i, j] = Element(ElementType.EMPTY if elem.age <= Game.RUBBLE_AGE else ElementType.RUBBLE)
                    break

    def calc_group(self, row, col, condition):
        """ Flood-fill algorithm to find contiguous elements meeting a condition """
        group = set()
        self.calc_group_rec(row, col, condition, group)
        return group

    def calc_group_rec(self, row, col, condition, group):
        if self.in_bounds(row, col) and condition(self[row, col]) and (row, col) not in group:
            group.add((row, col))
            for drow, dcol in Game.NEIGHBORS:
                self.calc_group_rec(row+drow, col+dcol, condition, group)


class PlayBoard(wx.Frame):
    """ Main GUI Window for actual gameplay """
    time_limit_flag = 0
    swap_storage_flag = 0
    t = 0
    play_sound = True
    
    def __init__(self, *args, **kwds):
        # Audio Initialization
        self.snd_pop = wx.adv.Sound(".\\pop.wav")
        self.snd_clock = wx.adv.Sound(".\\reloj.wav")
        self.snd_tick = wx.adv.Sound(".\\tick.wav")
        self.snd_finish = wx.adv.Sound(".\\Fin.wav")
        self.snd_wick = wx.adv.Sound(".\\Wick.wav")

        self.game_over_screen = GameOverFrame(None, wx.ID_ANY, "")
        self.game = Game()

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetTitle("Suburbious")
        
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap(".\\icono.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        self.timer = wx.Timer(self) 

        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(240, 170, 120))

        self.main_sizer_horiz = wx.BoxSizer(wx.HORIZONTAL)
        self.sidebar_sizer_vert = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer_horiz.Add(self.sidebar_sizer_vert, 1, wx.EXPAND, 0)

        # Top Controls (New Game & Timer Toggle)
        self.controls_sizer_horiz = wx.BoxSizer(wx.HORIZONTAL)
        self.sidebar_sizer_vert.Add(self.controls_sizer_horiz, 0, wx.EXPAND, 0)

        self.btn_new_game = wx.Button(self.panel, wx.ID_ANY, "New Game")
        self.btn_new_game.SetFont(wx.Font(20, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        self.controls_sizer_horiz.Add(self.btn_new_game, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 0)

        self.chk_time_limit = wx.CheckBox(self.panel, wx.ID_ANY, u"Time Limit")
        self.chk_time_limit.SetValue(self.time_limit_flag == 1)
        self.controls_sizer_horiz.Add(self.chk_time_limit, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        # Storage and Current Element Section
        self.items_sizer_horiz = wx.BoxSizer(wx.HORIZONTAL)
        self.sidebar_sizer_vert.Add(self.items_sizer_horiz, 0, wx.EXPAND, 0)

        self.storage_box_sizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, wx.ID_ANY, u"Storage"), wx.VERTICAL)
        self.items_sizer_horiz.Add(self.storage_box_sizer, 1, 0, 0)

        # REFACTOR: Using get_image_path removes the massive IF block
        img_storage = get_image_path(self.game.storage.type, self.game.storage.age)
        self.img_storage = wx.StaticBitmap(self.panel, wx.ID_ANY, wx.Bitmap(img_storage))
        self.img_storage.SetMinSize((125,125))
        self.storage_box_sizer.Add(self.img_storage, 0, wx.EXPAND, 0)

        self.btn_swap = wx.BitmapButton(self.panel, wx.ID_ANY, wx.Bitmap(".\\Intercambio.png"))
        self.btn_swap.SetMinSize(wx.Size(150, 100))
        self.items_sizer_horiz.Add(self.btn_swap, 1, wx.EXPAND, 0)

        self.current_box_sizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, wx.ID_ANY, "Current"), wx.VERTICAL)
        self.items_sizer_horiz.Add(self.current_box_sizer, 1, wx.EXPAND, 0)

        # REFACTOR: Using get_image_path removes the massive IF block
        img_current = get_image_path(self.game.current.type, self.game.current.age)
        self.img_current = wx.StaticBitmap(self.panel, wx.ID_ANY, wx.Bitmap(img_current))
        self.img_current.SetMinSize((125,125))
        self.current_box_sizer.Add(self.img_current, 0, wx.EXPAND, 0)

        # Score Section
        self.score_box_horiz = wx.StaticBoxSizer(wx.StaticBox(self.panel, wx.ID_ANY, u"Score"), wx.HORIZONTAL)
        self.sidebar_sizer_vert.Add(self.score_box_horiz, 0, wx.EXPAND, 0)

        self.score_box_vert = wx.BoxSizer(wx.VERTICAL)
        self.score_box_horiz.Add(self.score_box_vert, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.lbl_score = wx.StaticText(self.panel, wx.ID_ANY, str(self.game.calculate_score()), style=wx.TE_CENTRE)
        self.lbl_score.SetFont(wx.Font(50, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        
        if self.game.calculate_score() > 0:
            self.lbl_score.SetForegroundColour(wx.Colour(0, 115, 50))
        else:
            self.lbl_score.SetForegroundColour(wx.Colour(200, 0, 0))
            
        self.score_box_vert.Add(self.lbl_score, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 0)

        # Decorative Middle Panel
        self.decor_panel = wx.Panel(self.panel, wx.ID_ANY)
        self.decor_panel.SetBackgroundColour(wx.Colour(240, 170, 120))

        image = wx.Bitmap(".\\Cuadro.jpg")
        static_image = wx.StaticBitmap(self.decor_panel, wx.ID_ANY, image)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(static_image, 1, wx.EXPAND)

        self.decor_panel.SetSizer(panel_sizer)
        self.decor_panel.SetMinSize((500, 350))
        self.sidebar_sizer_vert.Add(self.decor_panel, 0, wx.EXPAND, 0)

        # Timer Section
        self.time_box_horiz = wx.StaticBoxSizer(wx.StaticBox(self.panel, wx.ID_ANY, "Time Remaining"), wx.HORIZONTAL)
        self.sidebar_sizer_vert.Add(self.time_box_horiz, 0, wx.EXPAND, 0)

        self.time_box_vert = wx.BoxSizer(wx.VERTICAL)
        self.time_box_horiz.Add(self.time_box_vert, 1, 0, 0)

        self.lbl_time = wx.StaticText(self.panel, wx.ID_ANY, "-", style=wx.ALIGN_CENTER_HORIZONTAL)
        self.lbl_time.SetFont(wx.Font(50, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        self.time_box_vert.Add(self.lbl_time, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 0)

        self.lbl_messages = wx.StaticText(self.panel, wx.ID_ANY, "Click on a board cell to place the piece")
        self.lbl_messages.SetFont(wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.sidebar_sizer_vert.Add(self.lbl_messages, 0, wx.EXPAND | wx.TOP, 10)

        # Main Board Grid
        self.board_grid = wx.GridSizer(self.game.NUM_ROWS, self.game.NUM_COLS, 30, 10)
        self.main_sizer_horiz.Add(self.board_grid, 10, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_cell = None 

        # REFACTOR: This replaces ~120 lines of redundant code while keeping the exact original size calculation
        for i in range(self.game.NUM_ROWS):
            for j in range(self.game.NUM_COLS):
                elem = self.game.board[i][j]
                img_path = get_image_path(elem.type, elem.age)
                
                self.btn_cell = wx.BitmapButton(self.panel, wx.ID_ANY, wx.Bitmap(img_path))
                
                # ORIGINAL MATH: Ensuring buttons scale properly when opening
                avail_w, avail_h = self.GetClientSize()
                btn_w = avail_w // self.game.NUM_ROWS 
                btn_h = avail_h // self.game.NUM_COLS 
                btn_size = max(btn_w, btn_h) + 50  
                
                self.btn_cell.SetMinSize(wx.Size(btn_size, btn_size))
                self.btn_cell.SetId(i * self.game.NUM_COLS + j)  
                self.btn_cell.Bind(wx.EVT_BUTTON, self.on_board_click)  
                self.board_grid.Add(self.btn_cell, 0)  
        
        self.panel.SetSizer(self.main_sizer_horiz)

        self.Maximize()
        self.Layout()

        # Event Binds
        self.Bind(wx.EVT_BUTTON, self.on_new_game_start, self.btn_new_game)
        self.Bind(wx.EVT_CHECKBOX, self.on_time_limit, self.chk_time_limit)
        self.Bind(wx.EVT_BUTTON, self.on_swap, self.btn_swap)
        self.Bind(wx.EVT_TIMER, self.on_time_tick)  

        self.refresh_game()
        self.Layout()

    def refresh_game(self):
        """ Updates the UI every time a turn is completed """
        
        if self.chk_time_limit.GetValue():
            self.start_timer()
        else:
            self.stop_timer()
        
        if self.swap_storage_flag == 1:
            self.time_rem = self.t 
            self.swap_storage_flag = 0

        # REFACTOR: Dynamic image updating replaces massive IF statements
        self.img_storage.SetBitmap(wx.Bitmap(get_image_path(self.game.storage.type, self.game.storage.age)))
        self.img_current.SetBitmap(wx.Bitmap(get_image_path(self.game.current.type, self.game.current.age)))

        # Update points
        self.current_score = self.game.calculate_score()
        self.lbl_score.SetLabelText(str(self.current_score))
        
        if self.current_score > 0:
            self.lbl_score.SetForegroundColour(wx.Colour(0, 115, 50))
        else:
            self.lbl_score.SetForegroundColour(wx.Colour(200, 0, 0))

        # REFACTOR: Clean dynamic board iteration
        self.btn_cell = None 
        for i in range(self.game.NUM_ROWS):
            for j in range(self.game.NUM_COLS):
                elem = self.game.board[i][j]
                self.btn_cell = self.FindWindowById(i * self.game.NUM_COLS + j)
                if self.btn_cell is not None:
                    self.btn_cell.SetBitmap(wx.Bitmap(get_image_path(elem.type, elem.age)))
                
        self.Maximize()
        self.Layout()
    
    def on_new_game_start(self, event): 
        self.snd_pop.Play(wx.adv.SOUND_ASYNC)
        tab_intro = MenuFrame(None, wx.ID_ANY, "")
        tab_intro.Show()
        self.Destroy()

    def on_time_limit(self, event): 
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)
        if self.chk_time_limit.GetValue():
            self.start_timer()
        else:
            self.stop_timer()
            self.lbl_time.SetLabelText("-") 
    
    def start_timer(self):
        self.time_rem = 10 
        self.timer.Start(1000) 
    
    def stop_timer(self):
        self.timer.Stop() 
    
    def on_time_tick(self, event):
        self.time_rem -= 1
        if self.time_rem % 2 != 0:
            self.snd_clock.Play(wx.adv.SOUND_ASYNC)
            
        self.t = self.time_rem
        self.lbl_time.SetLabelText(str(self.time_rem)) 
        
        if self.time_rem <= 0:
            self.stop_timer()
            raffle = []

            for i in range(self.game.NUM_ROWS):
                for j in range(self.game.NUM_COLS):
                    if self.game.current.type == ElementType.WICK:  
                        if self.game.board[i][j].type != ElementType.EMPTY:  
                            raffle.append((i,j))
                    else:  
                        if self.game.board[i][j].type == ElementType.EMPTY:   
                            raffle.append((i,j))
            
            raffled_elem = random.choice(raffle)
            i = raffled_elem[0]
            j = raffled_elem[1]
            if self.game.play_turn(i, j):
                self.snd_finish.Play(wx.adv.SOUND_ASYNC)
                self.game_over_screen.Show()
            self.refresh_game()
                                        
    def on_swap(self, event): 
        self.game.swap_storage()
        self.swap_storage_flag = 1
        self.snd_pop.Play(wx.adv.SOUND_ASYNC)
        self.refresh_game()

    def save_record(self):
        """ REFACTOR: Encapsulated logic for saving high scores to prevent code repetition. """
        try:
            # Ensure the file exists before reading
            if not os.path.exists("record.txt"):
                with open("record.txt", "w") as f:
                    f.write("0\n")

            with open("record.txt", "r") as file:
                lines = file.readlines()
            
            with open("record.txt", "w") as file:
                for linea in lines:
                    numero = int(linea.strip())
                    file.truncate(0)
                    if numero < self.current_score:
                        file.write(str(self.current_score) + "\n")
                    else:
                        file.write(str(numero) + "\n")
        
        except FileNotFoundError:
            print("Error opening record file")

    def on_board_click(self, event): 
        boton_id = event.GetId()  
        i = boton_id // self.game.NUM_COLS 
        j = boton_id % self.game.NUM_COLS 
        action_performed = 0
        
        # Behavior if holding WICK
        if self.game.current.type == ElementType.WICK:
            if self.game.board[i][j].type == ElementType.EMPTY:
                self.lbl_messages.SetLabelText("You must use the Wick on an occupied cell")
                self.swap_storage_flag = 1
                self.refresh_game()
            else:
                if self.game.play_turn(i, j):
                    action_performed = 1
                    self.current_score = self.game.calculate_score()
                    self.save_record()
                    self.snd_finish.Play(wx.adv.SOUND_ASYNC)
                    self.game_over_screen.Show()        
                
                self.lbl_messages.SetLabelText("Click on a board cell to place the piece")
                if self.swap_storage_flag == 0:
                    self.time_rem = 10  
                self.swap_storage_flag = 0
                self.snd_wick.Play(wx.adv.SOUND_ASYNC)
                self.refresh_game()

        # Standard element placement
        else:
            if self.game.board[i][j].type != ElementType.EMPTY:
                self.lbl_messages.SetLabelText("That cell is occupied")
                self.swap_storage_flag = 1
                self.refresh_game()
            else:
                if self.game.play_turn(i, j):
                    action_performed = 1
                    self.current_score = self.game.calculate_score()
                    self.save_record()
                    self.snd_finish.Play(wx.adv.SOUND_ASYNC)
                    self.game_over_screen.Show()  
                
                self.lbl_messages.SetLabelText("Click on a board cell to place the piece")
                if self.swap_storage_flag == 0:
                    self.time_rem = 10  
                self.swap_storage_flag = 0
                self.refresh_game()
            
            if action_performed == 0:
                if self.play_sound:
                    self.snd_pop.Play(wx.adv.SOUND_ASYNC)
    
class ConfigDialog(wx.Dialog):
    """ Game configuration dialog """
    def __init__(self, *args, **kwds):
        self.limtiem = 0

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetSize((400, 175))
        self.Centre()
        self.SetTitle("New Game")
        
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap(".\\icono.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        Sizer_horizontal_no_btns = wx.BoxSizer(wx.VERTICAL)
        Sizer_vertical_no_btns = wx.BoxSizer(wx.HORIZONTAL)
        Sizer_horizontal_no_btns.Add(Sizer_vertical_no_btns, 0, wx.EXPAND, 0)

        New_Game_Box = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "New Game Setup"), wx.VERTICAL)
        Sizer_vertical_no_btns.Add(New_Game_Box, 1, wx.EXPAND, 0)

        self.Radio_File = wx.RadioButton(self, wx.ID_ANY, "Read from File")
        self.Radio_File.SetValue(False)
        New_Game_Box.Add(self.Radio_File, 0, 0, 0)

        self.Radio_Random_6x6 = wx.RadioButton(self, wx.ID_ANY, "Create Random (6x6)")
        self.Radio_Random_6x6.SetValue(True)
        
        Game.read_file = False
        Game.create_random = True
        Game.create_custom_size = False
        Game.NUM_ROWS = 6
        Game.NUM_COLS = 6
        New_Game_Box.Add(self.Radio_Random_6x6, 0, 0, 0)

        self.Radio_Custom = wx.RadioButton(self, wx.ID_ANY, u"Create Random (choose size)")
        self.Radio_Custom.SetValue(False)
        New_Game_Box.Add(self.Radio_Custom, 0, 0, 0)

        self.Sizer_horizontal_board_size = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, u"Board Size"), wx.VERTICAL)
        Sizer_vertical_no_btns.Add(self.Sizer_horizontal_board_size, 1, wx.EXPAND, 0)

        Sizer_horizontal_rows = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer_horizontal_board_size.Add(Sizer_horizontal_rows, 1, wx.ALIGN_RIGHT, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, u"Nº Rows = ")
        Sizer_horizontal_rows.Add(label_1, 0, 0, 0)

        self.Num_Rows = wx.SpinCtrl(self, wx.ID_ANY, "6", min=1, max=10)
        Sizer_horizontal_rows.Add(self.Num_Rows, 0, 0, 0)

        Sizer_horizontal_cols = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer_horizontal_board_size.Add(Sizer_horizontal_cols, 1, wx.ALIGN_RIGHT, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, u"Nº Cols = ")
        Sizer_horizontal_cols.Add(label_2, 0, 0, 0)

        self.Num_Cols = wx.SpinCtrl(self, wx.ID_ANY, "6", min=1, max=10)
        Sizer_horizontal_cols.Add(self.Num_Cols, 0, 0, 0)

        Btns_Ok_Cancel = wx.StdDialogButtonSizer()
        Sizer_horizontal_no_btns.Add(Btns_Ok_Cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.Btn_Ok = wx.Button(self, wx.ID_OK, "")
        self.Btn_Ok.SetDefault()
        Btns_Ok_Cancel.AddButton(self.Btn_Ok)

        self.Btn_Cancel = wx.Button(self, wx.ID_CANCEL, "")
        Btns_Ok_Cancel.AddButton(self.Btn_Cancel)
        Btns_Ok_Cancel.Realize()

        self.SetSizer(Sizer_horizontal_no_btns)
        self.Sizer_horizontal_board_size.ShowItems(False)
        self.Layout()

        self.Bind(wx.EVT_RADIOBUTTON, self.on_read_file, self.Radio_File)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_create_random, self.Radio_Random_6x6)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_create_custom, self.Radio_Custom)
        self.Bind(wx.EVT_SPINCTRL, self.on_change_rows, self.Num_Rows)
        self.Bind(wx.EVT_SPINCTRL, self.on_change_cols, self.Num_Cols)
        self.Bind(wx.EVT_BUTTON, self.on_confirm, self.Btn_Ok)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, self.Btn_Cancel)

        self.snd_tick = wx.adv.Sound(".\\tick.wav")

    def on_read_file(self, event): 
        self.Sizer_horizontal_board_size.ShowItems(False)
        dialog = wx.FileDialog(None, "Select File", "", "", "Text Files (*.txt)|*.txt", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            selected_file = dialog.GetPath()
            Game.file_path = selected_file
        self.Layout()
        dialog.Destroy()

        Game.read_file = True
        Game.create_random = False
        Game.create_custom_size = False
        Game.NUM_ROWS = 6
        Game.NUM_COLS = 6
        
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)

    def on_create_random(self, event): 
        self.Sizer_horizontal_board_size.ShowItems(False)
        self.Layout()
        Game.read_file = False
        Game.create_random = True
        Game.create_custom_size = False
        Game.NUM_ROWS = 6
        Game.NUM_COLS = 6

        self.snd_tick.Play(wx.adv.SOUND_ASYNC)

    def on_create_custom(self, event): 
        self.Sizer_horizontal_board_size.ShowItems(True)
        self.Layout()
        Game.read_file = False
        Game.create_random = False
        Game.create_custom_size = True

        self.snd_tick.Play(wx.adv.SOUND_ASYNC)

    def on_change_rows(self, event): 
        Game.NUM_ROWS = self.Num_Rows.GetValue()
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)

    def on_change_cols(self, event): 
        Game.NUM_COLS = self.Num_Cols.GetValue()
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)

    def on_confirm(self, event): 
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)
        self.Tab_Play = PlayBoard(None, wx.ID_ANY, "")
        self.Hide()
        self.Tab_Play.Show()

    def on_cancel(self, event): 
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)
        tab_intro = MenuFrame(None, wx.ID_ANY, "")
        tab_intro.Show()
        self.Destroy()


class IntroFrame(wx.Frame):
    """ Splash Screen UI upon initialization """
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.ShowFullScreen(True)
        self.Maximize()
        self.SetTitle("Suburbious")
        
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap(".\\icono.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        self.background_panel = wx.Panel(self, wx.ID_ANY)
        self.background_panel.SetBackgroundColour(wx.Colour(240, 170, 120))

        Sizer_horizontal_all = wx.BoxSizer(wx.VERTICAL)
        self.space_above_title = wx.Panel(self.background_panel, wx.ID_ANY)
        Sizer_horizontal_all.Add(self.space_above_title, 1, wx.EXPAND, 0)

        Sizer_vertical_title = wx.BoxSizer(wx.HORIZONTAL)
        Sizer_horizontal_all.Add(Sizer_vertical_title, 2, wx.ALIGN_CENTER_HORIZONTAL, 0)

        Title = wx.StaticText(self.background_panel, wx.ID_ANY, "Suburbious")
        Title.SetFont(wx.Font(125, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        Sizer_vertical_title.Add(Title, 10, 0, 0)

        imagen = wx.Bitmap(".\\Intro.png", wx.BITMAP_TYPE_ANY)
        imagen_static = wx.StaticBitmap(self.background_panel, wx.ID_ANY, imagen, size = (800,400))
        Sizer_horizontal_all.Add(imagen_static, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.btn_start = wx.Button(self.background_panel, wx.ID_ANY, "Start")
        self.btn_start.SetFont(wx.Font(25, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        self.btn_start.SetBackgroundColour(wx.Colour(255, 255, 255))
        Sizer_horizontal_all.Add(self.btn_start, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.background_panel.SetSizer(Sizer_horizontal_all)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_start, self.btn_start)

        self.snd_intro = wx.adv.Sound(".\\Intro.wav")
        self.snd_intro.Play(wx.adv.SOUND_ASYNC)

    def on_start(self, event): 
        self.snd_pop = wx.adv.Sound(".\\pop.wav")
        self.snd_pop.Play(wx.adv.SOUND_ASYNC)
        tab_intro = MenuFrame(None, wx.ID_ANY, "")
        tab_intro.Show()
        self.Destroy()

class MenuFrame(wx.Frame):
    """ Secondary Menu UI linking to configuration settings """
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((400, 300))
        self.SetTitle("Suburbious")
        
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap(".\\icono.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        self.panel_1 = wx.Panel(self, wx.ID_ANY)

        Sizer_parte_sin_tablero_vertical = wx.BoxSizer(wx.HORIZONTAL)
        Sizer_parte_sin_tablero_horizontal = wx.BoxSizer(wx.VERTICAL)
        Sizer_parte_sin_tablero_vertical.Add(Sizer_parte_sin_tablero_horizontal, 3, wx.EXPAND, 0)

        Sizer_boton_nueva_partida = wx.BoxSizer(wx.HORIZONTAL)
        Sizer_parte_sin_tablero_horizontal.Add(Sizer_boton_nueva_partida, 0, wx.EXPAND, 0)

        self.btn_new_game = wx.Button(self.panel_1, wx.ID_ANY, "New Game")
        self.btn_new_game.SetFont(wx.Font(10, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Algerian"))
        Sizer_boton_nueva_partida.Add(self.btn_new_game, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 0)

        self.chk_time_limit = wx.CheckBox(self.panel_1, wx.ID_ANY, u"Time Limit")
        self.chk_time_limit.SetValue(0)
        Sizer_boton_nueva_partida.Add(self.chk_time_limit, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        Sizer_vertical_almacen_y_actual = wx.BoxSizer(wx.HORIZONTAL)
        Sizer_parte_sin_tablero_horizontal.Add(Sizer_vertical_almacen_y_actual, 0, wx.EXPAND, 0)

        Sizer_almacen_horizontal = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, u"Storage"), wx.VERTICAL)
        Sizer_vertical_almacen_y_actual.Add(Sizer_almacen_horizontal, 1, 0, 0)

        self.txt_storage = wx.TextCtrl(self.panel_1, wx.ID_ANY, ".", style=wx.TE_CENTRE)
        Sizer_almacen_horizontal.Add(self.txt_storage, 0, wx.EXPAND, 0)

        self.btn_swap = wx.BitmapButton(self.panel_1, wx.ID_ANY, wx.Bitmap(".\\Intercambio.png"))
        self.btn_swap.SetMinSize(wx.Size(125, 75))
        Sizer_vertical_almacen_y_actual.Add(self.btn_swap, 0, 0)

        Sizer_actual_horizontal = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, "Current"), wx.VERTICAL)
        Sizer_vertical_almacen_y_actual.Add(Sizer_actual_horizontal, 1, wx.EXPAND, 0)

        self.txt_current = wx.TextCtrl(self.panel_1, wx.ID_ANY, ".", style=wx.TE_CENTRE)
        Sizer_actual_horizontal.Add(self.txt_current, 0, wx.EXPAND, 0)

        Sizer_vertical_puntuacion = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, u"Score"), wx.HORIZONTAL)
        Sizer_parte_sin_tablero_horizontal.Add(Sizer_vertical_puntuacion, 0, wx.EXPAND, 0)

        Sizer_horizontal_puntuacion = wx.BoxSizer(wx.VERTICAL)
        Sizer_vertical_puntuacion.Add(Sizer_horizontal_puntuacion, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        Puntuacion = wx.StaticText(self.panel_1, wx.ID_ANY, "0", style=wx.ALIGN_CENTER_HORIZONTAL)
        Puntuacion.SetFont(wx.Font(30, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        Sizer_horizontal_puntuacion.Add(Puntuacion, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 0)

        self.Space_Panel_Middle = wx.Panel(self.panel_1, wx.ID_ANY)
        self.Space_Panel_Middle.SetBackgroundColour(wx.Colour(170, 170, 170))
        Sizer_parte_sin_tablero_horizontal.Add(self.Space_Panel_Middle, 1, wx.EXPAND, 0)

        Sizer_vertical_tiempo_restante = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, "Time Remaining"), wx.HORIZONTAL)
        Sizer_parte_sin_tablero_horizontal.Add(Sizer_vertical_tiempo_restante, 0, wx.EXPAND, 0)

        Sizer_horizontal_tiempo_restante = wx.BoxSizer(wx.VERTICAL)
        Sizer_vertical_tiempo_restante.Add(Sizer_horizontal_tiempo_restante, 1, 0, 0)

        Tiempo_Restante = wx.StaticText(self.panel_1, wx.ID_ANY, "-", style=wx.ALIGN_CENTER_HORIZONTAL)
        Tiempo_Restante.SetFont(wx.Font(30, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        Sizer_horizontal_tiempo_restante.Add(Tiempo_Restante, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 0)

        Messages = wx.StaticText(self.panel_1, wx.ID_ANY, "Press [New Game] to start playing!")
        Messages.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        Sizer_parte_sin_tablero_horizontal.Add(Messages, 0, wx.EXPAND | wx.TOP, 10)

        self.panel_1.SetSizer(Sizer_parte_sin_tablero_vertical)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_new_game, self.btn_new_game)
        self.Bind(wx.EVT_CHECKBOX, self.on_time_limit, self.chk_time_limit)

    def on_new_game(self, event): 
        self.snd_pop = wx.adv.Sound(".\\pop.wav")
        self.snd_pop.Play(wx.adv.SOUND_ASYNC)
        self.configurator = ConfigDialog(None, wx.ID_ANY, "")
        self.Hide()
        self.configurator.Show()

    def on_time_limit(self, event): 
        self.snd_tick = wx.adv.Sound(".\\tick.wav")
        self.snd_tick.Play(wx.adv.SOUND_ASYNC)
        if self.chk_time_limit.GetValue():
            PlayBoard.limtiem = 1
        else:
            PlayBoard.limtiem = 0
        
        event.Skip()

class GameOverFrame(wx.Frame):
    """ Simple display frame to show when the game is over """
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", wx.DEFAULT_FRAME_STYLE)
        wx.Frame.__init__(self, *args, **kwds)
        self.Maximize()
        self.SetTitle("Suburbious")

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap(".\\icono.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        self.fin_panel = wx.Panel(self)
        image = wx.Image(".\\GameOver.jpg", wx.BITMAP_TYPE_ANY)
        
        # We ensure width and height are valid to prevent exceptions
        ancho, alto = self.GetSize()
        if ancho > 0 and alto > 0:
            image = image.Scale(ancho, alto)
            
        bitmap = wx.StaticBitmap(self.fin_panel, wx.ID_ANY, wx.Bitmap(image))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(bitmap, 1, wx.EXPAND)
        self.fin_panel.SetSizer(sizer)
        self.fin_panel.SetSizeHints(-1, -1, -1, -1) 

        sizer_principal = wx.BoxSizer(wx.VERTICAL)
        sizer_principal.Add(self.fin_panel, 1, wx.EXPAND)
        self.SetSizer(sizer_principal)
    
class SuburbiousApp(wx.App):
    def OnInit(self):
        self.Intro = IntroFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.Intro)
        self.Intro.Show()
        return True

def get_letter(i):
    """ 
    Returns the i-th letter starting from A
    :param i: 0-based index
    :return: i-th letter
    """
    return chr(ord('A') + i)
    
if __name__ == '__main__':
    app = SuburbiousApp(False)
    app.MainLoop()