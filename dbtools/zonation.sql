SELECT distinct
    z.DB_SLDNID,
    trim(z.TIG_DESCRIPTION) AS "zonation_name"
FROM
    tig_zonation z
ORDER BY
    z.DB_INSTANCE_TIME_STAMP desc