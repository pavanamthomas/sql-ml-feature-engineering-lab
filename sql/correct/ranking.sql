-- ROW_NUMBER vs RANK vs DENSE_RANK on a known-tie score table.
-- Expected for scores 30, 20, 20, 20, 10 ordered DESC:
-- ROW_NUMBER: 1, 2, 3, 4, 5
-- RANK:       1, 2, 2, 2, 5
-- DENSE_RANK: 1, 2, 2, 2, 3

SELECT
    player_id,
    player,
    score,
    ROW_NUMBER() OVER (ORDER BY score DESC, player_id) AS rn,
    RANK() OVER (ORDER BY score DESC) AS rnk,
    DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rnk
FROM rank_demo
ORDER BY score DESC, player_id;
