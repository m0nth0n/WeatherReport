-- 1. Average, maximum, and minimum temperature per city per day.
SELECT
    city,
    date(time)                 AS day,
    ROUND(AVG(temperature), 2) AS avg_temp,
    ROUND(MAX(temperature), 2) AS max_temp,
    ROUND(MIN(temperature), 2) AS min_temp
FROM weather
WHERE date(time) BETWEEN date('now') AND date('now', '+6 days')
GROUP BY city, date(time)
ORDER BY city, day;


-- 2. Which city has the widest temperature range (max - min) over the next 7 days.
SELECT
    city,
    ROUND(MAX(temperature) - MIN(temperature), 2) AS temp_range
FROM weather
WHERE date(time) BETWEEN date('now') AND date('now', '+6 days')
GROUP BY city
ORDER BY temp_range DESC;


-- 3. The hour with the highest chance of rain per city, per day.
-- RANK() (not ROW_NUMBER) so tied max-probability hours all show up.
WITH ranked AS (
    SELECT
        city,
        date(time) AS day,
        time,
        precipitation_probability,
        RANK() OVER (
            PARTITION BY city, date(time)
            ORDER BY precipitation_probability DESC
        ) AS rnk
    FROM weather
    WHERE date(time) BETWEEN date('now') AND date('now', '+6 days')
)
SELECT city, day, time, precipitation_probability
FROM ranked
WHERE rnk = 1
ORDER BY city, day;


-- 4. (Harder) For each city, the difference in daily average temperature
-- compared to the previous day, using a window function (LAG).
WITH daily AS (
    SELECT
        city,
        date(time) AS day,
        ROUND(AVG(temperature), 2) AS avg_temp
    FROM weather
    WHERE date(time) BETWEEN date('now') AND date('now', '+6 days')
    GROUP BY city, date(time)
)
SELECT
    city,
    day,
    avg_temp,
    ROUND(avg_temp - LAG(avg_temp) OVER (PARTITION BY city ORDER BY day), 2) AS diff_from_prev_day
FROM daily
ORDER BY city, day;
