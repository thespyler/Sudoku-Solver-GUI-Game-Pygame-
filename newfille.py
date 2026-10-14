

import random
import sys
import pygame

# --------------------------------------------------------------------------
# Sudoku logic
# --------------------------------------------------------------------------
PEERS = {}
for _r in range(9):
    for _c in range(9):
        s = set()
        for i in range(9):
            s.add((_r, i))
            s.add((i, _c))
        br, bc = _r // 3 * 3, _c // 3 * 3
        for i in range(3):
            for j in range(3):
                s.add((br + i, bc + j))
        s.discard((_r, _c))
        PEERS[(_r, _c)] = s


def candidates(grid, r, c):
    used = {grid[pr][pc] for pr, pc in PEERS[(r, c)]}
    return [v for v in range(1, 10) if v not in used]


def best_cell(grid):
    """Empty cell with the fewest candidates (MRV heuristic)."""
    best = None
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                cands = candidates(grid, r, c)
                if best is None or len(cands) < len(best[2]):
                    best = (r, c, cands)
                    if len(cands) <= 1:
                        return best
    return best


def solve(grid, randomize=False):
    cell = best_cell(grid)
    if cell is None:
        return True
    r, c, cands = cell
    if randomize:
        random.shuffle(cands)
    for v in cands:
        grid[r][c] = v
        if solve(grid, randomize):
            return True
    grid[r][c] = 0
    return False


def count_solutions(grid, limit=2):
    cell = best_cell(grid)
    if cell is None:
        return 1
    r, c, cands = cell
    total = 0
    for v in cands:
        grid[r][c] = v
        total += count_solutions(grid, limit - total)
        if total >= limit:
            break
    grid[r][c] = 0
    return total


def solve_steps(grid):
    """Generator version of the solver that yields every placement/backtrack."""
    cell = best_cell(grid)
    if cell is None:
        return True
    r, c, cands = cell
    for v in cands:
        grid[r][c] = v
        yield (r, c, v)
        if (yield from solve_steps(grid)):
            return True
        grid[r][c] = 0
        yield (r, c, 0)
    return False


def find_conflicts(grid):
    bad = set()
    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v and any(grid[pr][pc] == v for pr, pc in PEERS[(r, c)]):
                bad.add((r, c))
    return bad


def generate(givens):
    """Return (puzzle, solution) with a unique solution."""
    full = [[0] * 9 for _ in range(9)]
    solve(full, randomize=True)
    puzzle = [row[:] for row in full]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    remaining = 81
    for r, c in cells:
        if remaining <= givens:
            break
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions([row[:] for row in puzzle]) != 1:
            puzzle[r][c] = backup
        else:
            remaining -= 1
    return puzzle, full



WIDTH, HEIGHT = 840, 700
GRID_X, GRID_Y, CELL = 30, 70, 60
GRID_SIZE = CELL * 9
PANEL_X = GRID_X + GRID_SIZE + 30

BG = (245, 247, 250)
WHITE = (255, 255, 255)
LINE_THIN = (200, 205, 214)
LINE_THICK = (40, 44, 52)
SEL = (187, 222, 251)
PEER = (232, 240, 250)
SAME = (255, 224, 178)
GIVEN_C = (30, 34, 42)
USER_C = (25, 118, 210)
SOLVER_C = (46, 150, 90)
ERR_C = (211, 47, 47)
ERR_BG = (255, 205, 210)
NOTE_C = (110, 118, 130)
BTN = (255, 255, 255)
BTN_HOVER = (225, 235, 248)
BTN_ACTIVE = (25, 118, 210)
BTN_BORDER = (190, 198, 210)
TEXT = (40, 44, 52)
MUTED = (115, 122, 135)

SPEEDS = [1, 2, 5, 10, 25, 100]


class Button:
    def __init__(self, rect, label, action, toggled=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.toggled = toggled  # callable returning bool, or None

    def draw(self, surf, font, mouse):
        active = self.toggled() if self.toggled else False
        hover = self.rect.collidepoint(mouse)
        color = BTN_ACTIVE if active else (BTN_HOVER if hover else BTN)
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, BTN_BORDER, self.rect, 1, border_radius=8)
        label = self.label() if callable(self.label) else self.label
        img = font.render(label, True, WHITE if active else TEXT)
        surf.blit(img, img.get_rect(center=self.rect.center))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Sudoku")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        names = "segoeui,helveticaneue,arial,dejavusans"
        self.f_big = pygame.font.SysFont(names, 36)
        self.f_title = pygame.font.SysFont(names, 30, bold=True)
        self.f_med = pygame.font.SysFont(names, 20)
        self.f_small = pygame.font.SysFont(names, 16)
        self.f_note = pygame.font.SysFont(names, 14)

        self.sel = (4, 4)
        self.notes_mode = False
        self.speed_idx = 2
        self.difficulty = "Medium"
        self._build_buttons()
        self.new_game("Medium")

    # setup
    def _build_buttons(self):
        x, w, h, gap = PANEL_X, 210, 38, 8
        y = 150
        specs = [
            ("Easy", lambda: self.new_game("Easy"), lambda: self.difficulty == "Easy" and self.mode == "play"),
            ("Medium", lambda: self.new_game("Medium"), lambda: self.difficulty == "Medium" and self.mode == "play"),
            ("Hard", lambda: self.new_game("Hard"), lambda: self.difficulty == "Hard" and self.mode == "play"),
            ("Custom puzzle", self.start_custom, lambda: self.mode == "custom"),
            (lambda: f"Notes: {'ON' if self.notes_mode else 'OFF'}", self.toggle_notes, lambda: self.notes_mode),
            ("Hint", self.hint, None),
            ("Check", self.check, None),
            ("Reset", self.reset, None),
            ("Solve (animated)", self.start_solve, None),
        ]
        self.buttons = []
        for label, action, tog in specs:
            self.buttons.append(Button((x, y, w, h), label, action, tog))
            y += h + gap

    def _blank(self):
        self.grid = [[0] * 9 for _ in range(9)]
        self.given = [[False] * 9 for _ in range(9)]
        self.notes = [[set() for _ in range(9)] for _ in range(9)]
        self.solver_cells = set()
        self.wrong = set()
        self.solving = None
        self.steps = 0
        self.finished = False
        self.elapsed = 0.0

    def new_game(self, difficulty):
        givens = {"Easy": 38, "Medium": 31, "Hard": 26}[difficulty]
        self.screen.fill(BG)
        msg = self.f_title.render("Generating puzzle...", True, TEXT)
        self.screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        pygame.display.flip()
        pygame.event.pump()

        self.difficulty = difficulty
        self.mode = "play"
        puzzle, self.solution = generate(givens)
        self._blank()
        self.puzzle = [row[:] for row in puzzle]
        for r in range(9):
            for c in range(9):
                self.grid[r][c] = puzzle[r][c]
                self.given[r][c] = puzzle[r][c] != 0
        self.message = f"New {difficulty.lower()} puzzle. Good luck!"

    def start_custom(self):
        self._blank()
        self.mode = "custom"
        self.solution = None
        self.message = "Enter your own puzzle, then press Solve."

    def reset(self):
        if self.mode == "custom":
            self.start_custom()
            return
        self.solving = None
        self.finished = False
        self.elapsed = 0.0
        self.steps = 0
        self.solver_cells.clear()
        self.wrong.clear()
        for r in range(9):
            for c in range(9):
                self.grid[r][c] = self.puzzle[r][c]
                self.notes[r][c].clear()
        self.message = "Puzzle reset."

    def toggle_notes(self):
        self.notes_mode = not self.notes_mode

    # ------------------------------------------------------------- gameplay
    def locked(self):
        return self.solving is not None or (self.finished and self.mode == "play")

    def set_value(self, r, c, v):
        if self.locked() or self.given[r][c]:
            return
        self.wrong.clear()
        if v and self.notes_mode and self.mode == "play":
            if self.grid[r][c] == 0:
                self.notes[r][c] ^= {v}
            return
        self.grid[r][c] = v
        self.notes[r][c].clear()
        if v:
            for pr, pc in PEERS[(r, c)]:
                self.notes[pr][pc].discard(v)
        if self.mode == "play":
            self.check_win()

    def check_win(self):
        if all(self.grid[r][c] for r in range(9) for c in range(9)) and not find_conflicts(self.grid):
            self.finished = True
            self.message = f"Solved in {self.fmt_time()}. Well done!"

    def hint(self):
        if self.mode != "play" or self.locked():
            return
        r, c = self.sel
        if self.grid[r][c] == self.solution[r][c]:
            empties = [(i, j) for i in range(9) for j in range(9)
                       if self.grid[i][j] != self.solution[i][j]]
            if not empties:
                return
            r, c = random.choice(empties)
            self.sel = (r, c)
        self.grid[r][c] = self.solution[r][c]
        self.notes[r][c].clear()
        self.wrong.clear()
        self.message = "Hint used."
        self.check_win()

    def check(self):
        if self.mode != "play" or self.locked():
            return
        self.wrong = {(r, c) for r in range(9) for c in range(9)
                      if self.grid[r][c] and self.grid[r][c] != self.solution[r][c]}
        self.message = (f"{len(self.wrong)} incorrect cell(s) highlighted."
                        if self.wrong else "No mistakes so far!")

    def start_solve(self):
        if self.solving is not None:
            return
        if self.mode == "custom":
            if find_conflicts(self.grid):
                self.message = "Puzzle has conflicting numbers."
                return
            if not any(v for row in self.grid for v in row):
                self.message = "Enter some numbers first."
                return
            test = [row[:] for row in self.grid]
            if not solve(test):
                self.message = "This puzzle has no solution."
                return
            self.solution = test
            for r in range(9):
                for c in range(9):
                    self.given[r][c] = self.grid[r][c] != 0
            self.puzzle = [row[:] for row in self.grid]
            self.mode = "play"
        # solve from the original clues only
        for r in range(9):
            for c in range(9):
                if not self.given[r][c]:
                    self.grid[r][c] = 0
                self.notes[r][c].clear()
        self.solver_cells.clear()
        self.wrong.clear()
        self.steps = 0
        self.finished = False
        self.solving = solve_steps(self.grid)
        self.message = "Solving with backtracking..."

    def step_solver(self):
        for _ in range(SPEEDS[self.speed_idx]):
            try:
                r, c, v = next(self.solving)
            except StopIteration:
                self.solving = None
                self.finished = True
                self.message = f"Solved by backtracking in {self.steps} steps."
                return
            self.steps += 1
            self.grid[r][c] = v
            if v:
                self.solver_cells.add((r, c))
            else:
                self.solver_cells.discard((r, c))

    # input
    def handle_key(self, event):
        k = event.key
        r, c = self.sel
        if k == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        moves = {pygame.K_UP: (-1, 0), pygame.K_DOWN: (1, 0),
                 pygame.K_LEFT: (0, -1), pygame.K_RIGHT: (0, 1)}
        if k in moves:
            dr, dc = moves[k]
            self.sel = ((r + dr) % 9, (c + dc) % 9)
        elif k in (pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_0, pygame.K_KP0):
            if self.notes_mode and self.mode == "play" and self.grid[r][c] == 0:
                if not self.locked():
                    self.notes[r][c].clear()
            else:
                self.set_value(r, c, 0)
        elif event.unicode in list("123456789"):
            self.set_value(r, c, int(event.unicode))
        elif k == pygame.K_n:
            self.toggle_notes()
        elif k == pygame.K_h:
            self.hint()
        elif k == pygame.K_c:
            self.check()
        elif k == pygame.K_s:
            self.start_solve()
        elif k == pygame.K_r:
            self.reset()
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_idx = max(0, self.speed_idx - 1)

    def handle_click(self, pos):
        x, y = pos
        if GRID_X <= x < GRID_X + GRID_SIZE and GRID_Y <= y < GRID_Y + GRID_SIZE:
            self.sel = ((y - GRID_Y) // CELL, (x - GRID_X) // CELL)
            return
        for b in self.buttons:
            if b.rect.collidepoint(pos):
                b.action()
                return

    # ------------------------------------------------------------- drawing
    def fmt_time(self):
        t = int(self.elapsed)
        return f"{t // 60:02d}:{t % 60:02d}"

    def draw(self):
        s = self.screen
        s.fill(BG)
        mouse = pygame.mouse.get_pos()

        title = self.f_title.render("Sudoku", True, TEXT)
        s.blit(title, (GRID_X, 18))

        # Board
        board = pygame.Rect(GRID_X, GRID_Y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(s, WHITE, board)
        sr, sc = self.sel
        sel_val = self.grid[sr][sc]
        conflicts = find_conflicts(self.grid)

        for r in range(9):
            for c in range(9):
                rect = pygame.Rect(GRID_X + c * CELL, GRID_Y + r * CELL, CELL, CELL)
                color = None
                if (r, c) == self.sel:
                    color = SEL
                elif (r, c) in PEERS[self.sel]:
                    color = PEER
                if sel_val and self.grid[r][c] == sel_val and (r, c) != self.sel:
                    color = SAME
                if (r, c) in self.wrong:
                    color = ERR_BG
                if color:
                    pygame.draw.rect(s, color, rect)

        # grid lines
        for i in range(10):
            thick = i % 3 == 0
            w = 3 if thick else 1
            col = LINE_THICK if thick else LINE_THIN
            pygame.draw.line(s, col, (GRID_X, GRID_Y + i * CELL),
                             (GRID_X + GRID_SIZE, GRID_Y + i * CELL), w)
            pygame.draw.line(s, col, (GRID_X + i * CELL, GRID_Y),
                             (GRID_X + i * CELL, GRID_Y + GRID_SIZE), w)

        # numbers and notes
        for r in range(9):
            for c in range(9):
                v = self.grid[r][c]
                x0 = GRID_X + c * CELL
                y0 = GRID_Y + r * CELL
                if v:
                    if (r, c) in conflicts:
                        col = ERR_C
                    elif self.given[r][c]:
                        col = GIVEN_C
                    elif (r, c) in self.solver_cells:
                        col = SOLVER_C
                    else:
                        col = USER_C
                    img = self.f_big.render(str(v), True, col)
                    s.blit(img, img.get_rect(center=(x0 + CELL // 2, y0 + CELL // 2 + 1)))
                    if self.given[r][c]:  # slight bold effect for clues
                        s.blit(img, img.get_rect(center=(x0 + CELL // 2 + 1, y0 + CELL // 2 + 1)))
                elif self.notes[r][c]:
                    for n in self.notes[r][c]:
                        nx = x0 + 10 + ((n - 1) % 3) * 20
                        ny = y0 + 10 + ((n - 1) // 3) * 20
                        img = self.f_note.render(str(n), True, NOTE_C)
                        s.blit(img, img.get_rect(center=(nx, ny)))

        # selection outline
        pygame.draw.rect(s, USER_C,
                         (GRID_X + sc * CELL, GRID_Y + sr * CELL, CELL, CELL), 3)
        pygame.draw.rect(s, LINE_THICK, board, 3)

        # Side panel
        mode_txt = "Custom entry" if self.mode == "custom" else self.difficulty
        s.blit(self.f_small.render("MODE", True, MUTED), (PANEL_X, 70))
        s.blit(self.f_med.render(mode_txt, True, TEXT), (PANEL_X, 90))
        s.blit(self.f_small.render("TIME", True, MUTED), (PANEL_X + 120, 70))
        s.blit(self.f_med.render(self.fmt_time() if self.mode == "play" else "--:--", True, TEXT),
               (PANEL_X + 120, 90))
        s.blit(self.f_small.render("NEW GAME", True, MUTED), (PANEL_X, 126))

        for i, b in enumerate(self.buttons):
            b.draw(s, self.f_med, mouse)

        speed = f"Solver speed: {SPEEDS[self.speed_idx]} step/frame  (+ / -)"
        s.blit(self.f_small.render(speed, True, MUTED), (PANEL_X, 150 + 9 * 46 + 6))
        if self.steps:
            s.blit(self.f_small.render(f"Steps: {self.steps}", True, MUTED),
                   (PANEL_X, 150 + 9 * 46 + 26))

        # Message bar
        s.blit(self.f_med.render(self.message, True, TEXT), (GRID_X, GRID_Y + GRID_SIZE + 18))
        legend = [("Given", GIVEN_C), ("You", USER_C), ("Solver", SOLVER_C), ("Conflict", ERR_C)]
        x = GRID_X
        for name, col in legend:
            pygame.draw.circle(s, col, (x + 6, GRID_Y + GRID_SIZE + 56), 6)
            img = self.f_small.render(name, True, MUTED)
            s.blit(img, (x + 18, GRID_Y + GRID_SIZE + 48))
            x += 30 + img.get_width() + 14

        pygame.display.flip()

    # ---------------------------------------------------------------- loop
    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            if self.solving is not None:
                self.step_solver()
            elif self.mode == "play" and not self.finished:
                self.elapsed += dt

            self.draw()


if __name__ == "__main__":
    Game().run()
