SELECT
    t.tig_curve_full_name,
    d.DB_INSTANCE_TIME_STAMP "Created",
    h.db_sldnid,
    i.tig_index_type,
    i.tig_index_track_top,
    i.tig_index_track_bot,
    i.tig_index_track_interval,
    i.tig_index_track_data,
    d.tig_curve_data_points,
    t.tig_default_scale_min,
    t.tig_default_scale_max,
    t.tig_log_or_linear_scale,
    t.tig_curve_co_mnemonic
FROM
    tig_curve_type t,
    tig_curve_header h,
    tig_curve_data d,
    tig_index_track i
where
    h.tig_well_sldnid = :wellid and
    h.tig_curve_type_sldnid = t.db_sldnid and
    h.tig_curve_data_sldnid = d.db_sldnid and
    h.tig_index_track_sldnid = i.db_sldnid and
    d.tig_curve_type_sldnid = t.db_sldnid and
    t.tig_curve_short_name = :typeName and
    t.tig_curve_co_mnemonic like :alias and
    h.tig_wireline_curv_status >= :status_min and h.tig_wireline_curv_status <= :status_max and
    h.tig_curve_edited_flag >= :edited_min and h.tig_curve_edited_flag <= :edited_max
order by
    d.db_instance_time_stamp desc

