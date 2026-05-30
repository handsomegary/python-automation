import sys
import time
from collections import defaultdict
from tqdm import tqdm
import multiprocessing as mp

# ==========================================
# 全域常數設定 (唯讀，方便多進程共享)
# ==========================================
POSITIONS = [
    (0, 2), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), 
    (2, 3), (2, 4), (3, 1), (3, 2), (3, 3), (4, 2)
]

POS_TO_IDX = {p: i for i, p in enumerate(POSITIONS)}

# 最佳搜尋順序：先填中心，再填交叉點
ORDER = [6, 1, 2, 3, 5, 7, 9, 10, 11, 0, 4, 8, 12]

# ==========================================
# 核心演算法與 Worker 函數
# ==========================================
def get_canonical(sol):
    """回傳 8 種對稱變換中字典序最小的一種 (Canonical Form)"""
    variants = []
    transforms = [
        lambda r, c: (r, c),           # 原圖
        lambda r, c: (c, 4-r),         # 90度
        lambda r, c: (4-r, 4-c),       # 180度
        lambda r, c: (4-c, r),         # 270度
        lambda r, c: (r, 4-c),         # 水平翻轉
        lambda r, c: (4-r, c),         # 垂直翻轉
        lambda r, c: (c, r),           # 主對角線翻轉
        lambda r, c: (4-c, 4-r)        # 副對角線翻轉
    ]
    
    for f in transforms:
        new_sol = [0] * 13
        for i in range(13):
            r, c = POSITIONS[i]
            nr, nc = f(r, c)
            new_sol[POS_TO_IDX[(nr, nc)]] = sol[i]
        variants.append(tuple(new_sol))
    
    return min(variants)

def solve_for_center(center_val):
    """
    Worker 函數：交由單一 CPU 核心執行。
    負責計算「當中心點固定為 center_val 時」的所有可能解。
    """
    local_results = defaultdict(set)
    assign = [None] * 13
    used = [False] * 14
    nums = list(range(1, 14))
    
    # 初始化這個核心負責的起點 (填入中心點)
    assign[6] = center_val
    used[center_val] = True
    
    def backtrack(step):
        if step == 13:
            # 當所有格子填完，必定是一組合法解，直接取得 Target Sum
            T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
            canonical = get_canonical(assign)
            local_results[T].add(canonical)
            return

        var = ORDER[step]
        for v in nums:
            if not used[v]:
                assign[var] = v
                ok = True
                
                # 🏆 O(1) 強效剪枝：在特定步驟直接檢查剛完成的線
                if step == 7: # 第三條線 (2,5,6,7,10) 填完
                    T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
                    if T < 28 or T > 42: 
                        ok = False
                elif step == 9: # 第一條線 (0,1,2,3,6) 填完
                    T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
                    if assign[0] + assign[1] + assign[2] + assign[3] + assign[6] != T: 
                        ok = False
                elif step == 10: # 第二條線 (1,4,5,6,9) 填完
                    T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
                    if assign[1] + assign[4] + assign[5] + assign[6] + assign[9] != T: 
                        ok = False
                elif step == 11: # 第四條線 (3,6,7,8,11) 填完
                    T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
                    if assign[3] + assign[6] + assign[7] + assign[8] + assign[11] != T: 
                        ok = False
                elif step == 12: # 第五條線 (6,9,10,11,12) 填完
                    T = assign[2] + assign[5] + assign[6] + assign[7] + assign[10]
                    if assign[6] + assign[9] + assign[10] + assign[11] + assign[12] != T: 
                        ok = False
                
                if ok:
                    used[v] = True
                    backtrack(step + 1)
                    used[v] = False
                    
                assign[var] = None

    # 從 step 1 開始遞迴 (因為 step 0 中心點已經填好了)
    backtrack(1)
    
    return local_results

# ==========================================
# 主程式區塊 (多進程發動機)
# ==========================================
if __name__ == '__main__':
    print("📊 啟動多核心極速平行運算模式 (Multiprocessing)...")
    print(f"🖥️  偵測到系統共有 {mp.cpu_count()} 個 CPU 核心")
    print("📐 數學推導邊界: target_sum 必定介於 28 至 42 之間\n")
    
    start_time = time.time()
    
    # 用來收集所有 CPU 算完的總結果
    master_unique_solutions = defaultdict(set)
    
    # 建立 13 個獨立任務 (中心點 1~13)
    tasks = list(range(1, 14))
    
    # 建立進程池，processes=13 代表最多同時派 13 個核心下去跑
    with mp.Pool(processes=13) as pool:
        # imap_unordered 會讓先算完的任務先回傳，搭配 tqdm 進度條最順暢
        results = list(tqdm(
            pool.imap_unordered(solve_for_center, tasks), 
            total=len(tasks), 
            desc="Exploring Tree", 
            unit=" branch"
        ))
        
        # 收集所有核心算出來的結果並合併
        for local_result in results:
            for T, canonical_set in local_result.items():
                master_unique_solutions[T].update(canonical_set)

    total_time = time.time() - start_time
    
    # ==========================================
    # 最終結果輸出
    # ==========================================
    print(f"\n✅ Search Completed in {total_time:.2f} seconds!")
    print("-" * 40)
    print(f"{'Target Sum':<15} | {'Distinct Solutions':<15}")
    print("-" * 40)
    
    max_solutions = 0
    best_target = None
    total_unique_count = 0
    
    # 排序並印出每個 target_sum 的分布
    for T in sorted(master_unique_solutions.keys()):
        count = len(master_unique_solutions[T])
        total_unique_count += count
        print(f"{T:<15} | {count:<15}")
        
        if count > max_solutions:
            max_solutions = count
            best_target = T
            
    print("-" * 40)
    print(f"🏆 Best Target Sum: {best_target} (with {max_solutions} unique solutions)")
    print(f"🌍 Total Unique Solutions Found: {total_unique_count}")
