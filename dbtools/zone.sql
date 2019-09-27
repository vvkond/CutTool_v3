SELECT
    TRIM(wh.TIG_LATEST_WELL_NAME) AS "well_name",
    TRIM(z.TIG_DESCRIPTION) AS "zonation_name",
    TRIM(i.TIG_INTERVAL_NAME) AS "zone_name",
    vi.TIG_TOP_POINT_DEPTH AS "top_depth",
    vi.TIG_BOT_POINT_DEPTH AS "bottom_depth",
    wh.DB_SLDNID AS "well_id",
    i.tig_background_colour
FROM
    tig_well_interval vi,
    tig_well_history wh,
    tig_interval i,
    tig_zonation z
WHERE
    wh.DB_SLDNID = :wellId
    AND wh.DB_SLDNID = vi.TIG_WELL_SLDNID
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
    AND(z.DB_SLDNID = :zonation_id OR :zonation_id IS NULL)
    --AND(i.DB_SLDNID = :zone_id OR :zone_id IS NULL)
