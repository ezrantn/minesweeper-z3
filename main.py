from board import MinesweeperBoard
from verifier import execute_z3_inference
from claude import call_claude_heuristic_strategist
from local_ai import call_local_ai_strategist

def main():
    # Inisialisasi papan Minesweeper (9x9 dengan 10 ranjau)
    board = MinesweeperBoard(width=9, height=9, total_mines=10)

    # 2. Lakukan klik pertama secara acak untuk membuka papan awal
    # (Karena di awal game seluruh papan masih 'U', Z3 belum punya konstrain untuk dinalar)
    board.reveal_cell(0, 0) 

    print("--- PAPAN AWAL (Setelah Klik Pertama) ---")
    board.display()

    # 3. Game Loop Otomatis Berbasis Z3
    print("--- Z3 MULAI MENGAMBIL ALIH PERMAINAN ---")
    while not board.game_over and not board.won:
        
        # Panggil fungsi Z3 dengan melempar state visible_board saat ini
        safe_moves, flag_moves = execute_z3_inference(
            board.visible_board, 
            board.width, 
            board.height, 
            board.total_mines
        )
        
        # Aksi A: Jika Z3 menemukan koordinat yang 100% aman, langsung klik!
        if safe_moves:
            for r, c in safe_moves:
                print(f"[Z3 DEDUCTION] Sel ({r}, {c}) terbukti AMAN. Mengklik...")
                board.reveal_cell(r, c)
                
        # Aksi B: Jika Z3 menemukan koordinat yang 100% ranjau, pasang bendera!
        elif flag_moves:
            for r, c in flag_moves:
                print(f"[Z3 DEDUCTION] Sel ({r}, {c}) terbukti RANJAU. Memasang Bendera...")
                board.flag_cell(r, c)
                
        # Aksi C: KEBUNTUAN LOGIKA (Deadlock)
        else:
            print("\n[DEADLOCK DETECTED] Z3 mentok secara matematis!")
            
            flat_board = [cell for row in board.visible_board for cell in row]
            mines_left = board.total_mines - flat_board.count('F')
            
            # Panggil Ollama untuk memotong jalan buntu
            r, c = call_local_ai_strategist(board.visible_board, board.width, board.height, mines_left)
            print(f"[LOCAL AI GUESS] Mencoba menerobos ke koordinat ({r}, {c})...\n")
            
            success = board.reveal_cell(r, c)
            if not success:
                print("[EXPLOSION] Ranjau meledak! Tebakan heuristik AI lokal meleset.")
                break

    # 4. Cek Hasil Akhir Simulasi Z3 + Ollama
    if board.won:
        print("Sukses! Kolaborasi Z3 + Llama3 menyapu bersih seluruh papan!")
    elif board.game_over:
        print("\n[RESULT] Kalah! Z3 menabrak bom (Harusnya mustahil terjadi kecuali salah konstrain).")
    else:
        print("\n[RESULT] Game dihentikan sementara di posisi deadlock.")


if __name__ == "__main__":
    main()
