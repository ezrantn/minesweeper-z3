import z3

def execute_z3_inference(visible_board, width, height, total_mines):
    """
    Mengeksekusi penalaran deduktif murni menggunakan SMT Z3.
    Mengembalikan list safe_moves dan flag_moves yang terbukti 100% akurat.
    """
    solver = z3.Solver()
    
    # 1. Inisialisasi matriks variabel Boolean dalam bentuk Integer Z3 (0 atau 1)
    z3_grid = [[z3.Int(f"x_{r}_{c}") for c in range(width)] for r in range(height)]
    
    # 2. Konstrain Dasar: Nilai setiap kotak harus biner (0 = Aman, 1 = Ranjau)
    for r in range(height):
        for c in range(width):
            solver.add(z3.And(z3_grid[r][c] >= 0, z3_grid[r][c] <= 1))
            
    # 3. Konstrain Global: Total ranjau di seluruh papan harus sesuai
    all_vars = [z3_grid[r][c] for r in range(height) for c in range(width)]
    solver.add(z3.Sum(all_vars) == total_mines)

    # 4. Konstrain Petunjuk Lokal: Memetakan angka di papan yang sudah terbuka
    for r in range(height):
        for c in range(width):
            val = visible_board[r][c]
            
            if isinstance(val, int):
                # Kotak yang sudah terbuka pastilah aman (bukan ranjau)
                solver.add(z3_grid[r][c] == 0)
                
                # Mengambil tetangga kotak
                neighbors = []
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < height and 0 <= nc < width:
                            neighbors.append((nr, nc))
                
                # Total sum variabel ranjau di tetangganya harus sama dengan angka petunjuk
                neighbor_vars = [z3_grid[nr][nc] for nr, nc in neighbors]
                solver.add(z3.Sum(neighbor_vars) == val)
                
            elif val == 'F':
                # Kotak yang sudah di-flag manual/sistem pasti bernilai 1 (ranjau)
                solver.add(z3_grid[r][c] == 1)

    # 5. Pembuktian Kontradiksi untuk menentukan langkah aman
    safe_moves = []
    flag_moves = []
    
    for r in range(height):
        for c in range(width):
            if visible_board[r][c] == 'U':
                # Tes A: Uji apakah kotak bisa menjadi ranjau
                # Hipotesis: Asumsikan kotak (r, c) adalah RANJAU (== 1)
                solver.push()
                solver.add(z3_grid[r][c] == 1)
                if solver.check() == z3.unsat:
                    # Jika kontradiktif (unsat), berarti kotak ini MUSTAHIL jadi ranjau.
                    # Kesimpulan: Kotak ini 100% AMAN.
                    safe_moves.append((r, c))
                solver.pop()
                
                # Tes B: Uji apakah kotak bisa menjadi aman
                # Hipotesis: Asumsikan kotak (r, c) adalah AMAN (== 0)
                solver.push()
                solver.add(z3_grid[r][c] == 0)
                if solver.check() == z3.unsat:
                    # Jika kontradiktif (unsat), berarti kotak ini MUSTAHIL aman.
                    # Kesimpulan: Kotak ini 100% RANJAU.
                    flag_moves.append((r, c))
                solver.pop()
                
    return safe_moves, flag_moves