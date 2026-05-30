# 參數設定：自己可以改這兩個
MAX_SOLUTIONS = 50      # 最多列出幾組解；設為 None 表示全部都列
TARGET_SUM   = 30       # 指定五條式子的共同總和；設為 None 表示不限

# --------------------------------------------------

positions = [
    (0, 2),  # 0
    (1, 1),  # 1
    (1, 2),  # 2
    (1, 3),  # 3
    (2, 0),  # 4
    (2, 1),  # 5
    (2, 2),  # 6 中心
    (2, 3),  # 7
    (2, 4),  # 8
    (3, 1),  # 9
    (3, 2),  # 10
    (3, 3),  # 11
    (4, 2),  # 12
]

# 五條等式用 index 表示
constraints = [
    [0, 1, 2, 3, 6],
    [1, 4, 5, 6, 9],
    [2, 5, 6, 7, 10],
    [3, 6, 7, 8, 11],
    [6, 9, 10, 11, 12],
]

nums = list(range(1, 14))  # 1~13
N = 13

assign = [None] * N        # 每個位置目前填什麼
used = [False] * 14        # 1~13 是否已用（忽略 index 0）

# 變數指派順序，先放中心再放四周，剪枝效果較好
order = [6, 1, 2, 3, 5, 7, 9, 10, 11, 0, 4, 8, 12]

found_count = 0  # 已找到幾組解


def print_grid(sol):
    """把解印成 5x5 陣列（其他位置印 0）"""
    grid = [[0] * 5 for _ in range(5)]
    for idx, val in enumerate(sol):
        r, c = positions[idx]
        grid[r][c] = val
    for row in grid:
        print(" ".join(f"{x:2d}" for x in row))


def partial_ok():
    """
    剪枝檢查：
    - 對每一條等式，如果已經 5 個都填完：
        - 它們彼此的和必須相等
        - 如果有設定 TARGET_SUM，也必須等於 TARGET_SUM
    """
    full_sums = []
    for S in constraints:
        s = 0
        unknown = 0
        for idx in S:
            if assign[idx] is None:
                unknown += 1
            else:
                s += assign[idx]
        if unknown == 0:
            full_sums.append(s)

    if not full_sums:
        # 還沒有任何一條等式完整，暫時都 OK
        return True

    # 完整的等式之間要互相相等
    if len(set(full_sums)) != 1:
        return False

    current_sum = full_sums[0]
    if TARGET_SUM is not None and current_sum != TARGET_SUM:
        # 有指定目標總和，但目前完整的等式和不等於它
        return False

    return True


def backtrack(pos):
    global found_count

    # 如果已經達到顯示上限，就不再繼續
    if MAX_SOLUTIONS is not None and found_count >= MAX_SOLUTIONS:
        return

    # 13 個位置都填完，檢查是不是一組合法解
    if pos == N:
        sums = [sum(assign[i] for i in S) for S in constraints]
        if len(set(sums)) == 1:       # 五條式子總和相等
            total_sum = sums[0]
            if TARGET_SUM is None or total_sum == TARGET_SUM:
                found_count += 1
                print(f"=== 解 #{found_count}，五條等式總和 = {total_sum} ===")
                print_grid(assign)
                print("-----------------------------\n")
        return

    var = order[pos]

    for v in nums:
        if used[v]:
            continue

        assign[var] = v
        used[v] = True

        if partial_ok():
            backtrack(pos + 1)

        # 還原
        assign[var] = None
        used[v] = False


# 執行搜尋
backtrack(0)

if found_count == 0:
    if TARGET_SUM is None:
        print("沒有找到任何解。")
    else:
        print(f"沒有找到總和為 {TARGET_SUM} 的解。")
else:
    print(f"共列出 {found_count} 組解（上限 = {MAX_SOLUTIONS}）。")
