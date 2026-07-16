import random

class MinesweeperBoard:
    def __init__(self, width=9, height=9, total_mines=10):
        self.width = width
        self.height = height
        self.total_mines = total_mines
        
        # 1. Matriks Rahasia (True Board): Tempat bom berada (1 = Bom, 0 = Aman)
        self.true_board = [[0 for _ in range(width)] for _ in range(height)]
        
        # 2. Matriks Publik (Visible Board): State yang dilihat oleh Z3 dan Claude
        # 'U' = Unexplored (Belum dibuka)
        # 'F' = Flagged (Ditandai bom)
        # 0-8 = Angka jumlah bom di sekitar kotak yang sudah dibuka
        self.visible_board = [['U' for _ in range(width)] for _ in range(height)]
        
        self.game_over = False
        self.won = False
        self._generate_mines()

    def _generate_mines(self):
        """Menyebarkan ranjau secara acak di papan"""
        mines_placed = 0
        while mines_placed < self.total_mines:
            r = random.randint(0, self.height - 1)
            c = random.randint(0, self.width - 1)
            if self.true_board[r][c] == 0:
                self.true_board[r][c] = 1
                mines_placed += 1

    def get_neighbors(self, r, c):
        """Mengembalikan list koordinat tetangga (maksimal 8 kotak sekitar)"""
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.height and 0 <= nc < self.width:
                    neighbors.append((nr, nc))
        return neighbors

    def _count_adjacent_mines(self, r, c):
        """Menghitung jumlah bom asli di sekitar kotak (r, c)"""
        return sum(self.true_board[nr][nc] for nr, nc in self.get_neighbors(r, c))

    def reveal_cell(self, r, c):
        """Aksi klik kiri: Membuka kotak"""
        if self.visible_board[r][c] != 'U':
            return True # Kotak sudah dibuka atau di-flag
        
        # ZONK! Kena ranjau
        if self.true_board[r][c] == 1:
            self.game_over = True
            return False
            
        # Hitung angka tetangga
        mine_count = self._count_adjacent_mines(r, c)
        self.visible_board[r][c] = mine_count
        
        # Flood fill otomatis jika angkanya 0 (tidak ada bom di sekitar)
        if mine_count == 0:
            for nr, nc in self.get_neighbors(r, c):
                if self.visible_board[nr][nc] == 'U':
                    self.reveal_cell(nr, nc)
                    
        self._check_win_condition()
        return True

    def flag_cell(self, r, c):
        """Aksi klik kanan: Menandai kotak yang dicurigai bom"""
        if self.visible_board[r][c] == 'U':
            self.visible_board[r][c] = 'F'
        elif self.visible_board[r][c] == 'F':
            self.visible_board[r][c] = 'U'

    def _check_win_condition(self):
        """Mengecek apakah semua kotak non-bom sudah berhasil dibuka"""
        for r in range(self.height):
            for c in range(self.width):
                if self.true_board[r][c] == 0 and self.visible_board[r][c] == 'U':
                    return
        self.won = True

    def display(self):
        """Visualisasi papan di terminal untuk mode debugging"""
        for row in self.visible_board:
            print(" ".join(str(cell) for cell in row))
        print("-" * (self.width * 2))