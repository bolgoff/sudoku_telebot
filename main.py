import telebot
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import easyocr
import io

class SudokuSolver:
    def __init__(self):
        pass

    def valid(self, grid, r, c, num):
        num_in_row = num not in grid[r]
        num_in_col = num not in [grid[i][c] for i in range(9)]
        num_in_sq = num not in [grid[i][j] for i in range(r, r // 3 * 3 + 3) for j in range(c, c // 3 * 3 + 3)]
        return num_in_row and num_in_col and num_in_sq

    def solve(self, grid, r, c):
        if r == 9:
            return True
        elif c == 9:
            return self.solve(grid, r + 1, 0)
        elif grid[r][c] != '.':
            return self.solve(grid, r, c + 1)
        else:
            for i in range(1, 10):
                if self.valid(grid, r, c, str(i)):
                    grid[r][c] = str(i)
                    if self.solve(grid, r, c+1):
                        return True
                    grid[r][c] = '.'
            return False

    def solve_sudoku(self, photo):
        img = cv2.imread(photo)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurry = cv2.GaussianBlur(gray, (5, 5), 5)
        thresh = cv2.adaptiveThreshold(blurry, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,57,5)
        cnts,_ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

        location = None
        for cnt in cnts:
            approx = cv2.approxPolyDP(cnt, 15, True)
            if len(approx) == 4:
                rect = np.zeros((4, 2), dtype = "float32")
                cutt = approx[:,0]

                diag_1 = cutt.sum(axis = 1)
                rect[0] = cutt[np.argmin(diag_1)]
                rect[2] = cutt[np.argmax(diag_1)]

                diag_2 = np.diff(cutt, axis = 1)
                rect[1] = cutt[np.argmin(diag_2)]
                rect[3] = cutt[np.argmax(diag_2)]

                location = rect
                break

        height = 900
        width = 900
        pts1 = np.float32([location[0], location[1], location[3], location[2]])
        pts2 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])

        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        board = cv2.warpPerspective(img, matrix, (width, height))

        reader = easyocr.Reader(['en'])
        df = pd.DataFrame(index=range(1, 10), columns=range(1, 10))
        sudoku_map = []
        split = np.split(board, 9, axis=1)
        for col,j  in enumerate(split):
            digs = np.split(j, 9)
            for row,d in enumerate(digs):
                d = d[10:90,10:90]
                cv2.copyMakeBorder(d,10,10,10,10,cv2.BORDER_CONSTANT)
                text = reader.readtext(d, allowlist='0123456789', detail=0)
                if len(text) > 0:
                    df.iloc[row, col] = text[0]
                    sudoku_map.append([text[0], str(row+1), str(col+1)])

        df.fillna('.', inplace=True)

        board = [list(df.iloc[i]) for i in range(9)]
        self.solve(board, 0, 0)
        return board

    def draw_sudoku(self, sudoku):
        buffer = io.BytesIO()
        fig, ax = plt.subplots()
        ax.set_xticks(np.arange(0, 10, 1))
        ax.set_yticks(np.arange(0, 10, 1))
        ax.grid(which='both')
        ax.xaxis.set_tick_params(width=0)
        ax.yaxis.set_tick_params(width=0)
        ax.set_xticks(np.arange(-.5, 9.5, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 9.5, 1), minor=True)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

        for i in range(0, 10):
            lw = 2 if i % 3 == 0 else 1
            ax.axhline(i-.5, color='k', linewidth=lw)
            ax.axvline(i-.5, color='k', linewidth=lw)

        ax.imshow(np.zeros((9, 9)), cmap='gray', extent=[-0.5, 8.5, -0.5, 8.5], alpha=0)

        for i in range(0, 9):
            for j in range(0, 9):
                ax.text(j, i, sudoku[i][j], ha='center', va='center', fontsize=15)
        plt.gca().invert_yaxis()
        plt.savefig(buffer, format='jpg', dpi=300)
        buffer.seek(0)
        plt.close(fig)
        return buffer

token = 'YOUR_TOKEN'

bot=telebot.TeleBot(token)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет! Я могу помочь тебе с решением судоку. Для этого пришли мне четкое фото головоломки, которую нужно решить!')

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, 'Начинаю решать...')
    try:
        solver = SudokuSolver()
        file_info = bot.get_file(message.photo[-1].file_id)
        file = bot.download_file(file_info.file_path)
        file_path = 'sudoku_photo.jpg'
        with open(file_path, 'wb') as f:
            f.write(file)
        solved_sudoku = solver.solve_sudoku(file_path)
        buffer = solver.draw_sudoku(solved_sudoku)
        bot.send_photo(message.chat.id, buffer, caption='Судоку решено!')
    except Exception as e:
        print(e)
        bot.reply_to(message, "Что-то пошло не так. Пожалуйста, попробуйте еще раз.")

bot.infinity_polling()

