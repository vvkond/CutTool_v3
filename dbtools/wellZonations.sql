SELECT distinct
    z.DB_SLDNID,
    TRIM(z.TIG_DESCRIPTION) AS "zonation_name"
FROM
    tig_well_interval vi,
    tig_well_history wh,
    tig_interval i,
    tig_zonation z
WHERE
    wh.DB_SLDNID {0}
    AND wh.DB_SLDNID = vi.TIG_WELL_SLDNID
    AND vi.TIG_INTERVAL_SLDNID = i.DB_SLDNID
    AND i.TIG_ZONATION_SLDNID = z.DB_SLDNID
