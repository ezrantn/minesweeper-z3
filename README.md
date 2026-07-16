# Minesweeper-Z3: Solving NP-Complete Puzzles via Neuro-Symbolic Reasoning

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Formulation: SMT Z3](https://img.shields.io/badge/Formulation-SMT%20Z3-orange.svg)](https://github.com/Z3Prover/z3)

This repository contains the official implementation and research framework for the paper: **"Solving NP-Complete Puzzles via Neuro-Symbolic Reasoning: A Local LLM-Guided Z3 Approach to Minesweeper"**.

The goal of this research is to bridge the gap between strict logic verification and probabilistic heuristics by combining an SMT Solver (**Z3**) with a Large Language Model via Ollama to conquer the NP-Complete problem of Minesweeper.

---

## The Neuro-Symbolic Architecture

Traditional AI approaches fail at Minesweeper when acting in isolation:

1. **The Symbolic Failure (Z3 Solver Only):** Falls into logical deadlocks when faced with incomplete information or 50-50 guesswork scenarios. It has no strategic framework to guess and simply stalls or fails randomly.
2. **The Connectionist Failure (LLM Only):** Suffers from spatial hallucinations, poor multi-step arithmetic grid tracking, and lacks any mathematical correctness guarantees.

Our **Neuro-Symbolic Framework** harmonizes both worlds:

* **Z3 as "The Logical Brain":** Maps the board into Boolean constraints and performs exact deductive inference via contradiction proofs. Guarantees 100% accurate safe clicks and flags as long as logical information is present.
* **LLM (Llama3) as "The Intuitive Strategist":** Invoked automatically *only* during logical deadlocks. It evaluates the macro-board state frontier and computes probabilistic heuristics to execute the optimal "strategic guess," breaking the deadlock and allowing Z3 to resume exact deduction.

---

## Getting Started

### Prerequisites

This project utilizes `uv` for ultra-fast Python package management. Ensure you have it installed along with [Ollama](https://ollama.com/) (if running local inference).

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ezrantn/minesweeper-z3.git
   cd minesweeper-z3
   ```
2. Install dependencies using uv:
   ```bash
   uv sync
   ```
3. Start the Llama3:
   ```bash
   ollama run llama3
   ```
4. Start simulation:
   ```bash
   uv run main.py
   ```