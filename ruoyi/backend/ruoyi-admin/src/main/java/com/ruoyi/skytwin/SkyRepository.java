package com.ruoyi.skytwin;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import com.ruoyi.common.exception.ServiceException;

/** Parameterized SQL only; JSON column names are camelCase. */
@Repository
public class SkyRepository {
    private final JdbcTemplate jdbc;
    public SkyRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public int update(String sql, Object... args) { return jdbc.update(sql, args); }
    public List<Map<String,Object>> rows(String sql, Object... args) {
        return jdbc.query(sql, SkyRepository::row, args);
    }
    public Map<String,Object> one(String sql, Object... args) {
        var rows = rows(sql,args);
        if (rows.isEmpty()) throw new ServiceException("记录不存在或已移除",404);
        return rows.get(0);
    }
    public long count(String sql, Object... args) { return jdbc.queryForObject(sql,Long.class,args); }
    private static Map<String,Object> row(ResultSet rs, int index) throws SQLException {
        Map<String,Object> result=new LinkedHashMap<>();
        var meta=rs.getMetaData();
        for(int i=1;i<=meta.getColumnCount();i++) {
            String[] parts=meta.getColumnLabel(i).split("_");
            StringBuilder name=new StringBuilder(parts[0]);
            for(int j=1;j<parts.length;j++) name.append(Character.toUpperCase(parts[j].charAt(0))).append(parts[j].substring(1));
            Object value=rs.getObject(i);
            if(value instanceof java.sql.Timestamp t) value=t.toLocalDateTime().toString();
            result.put(name.toString(),value);
        }
        return result;
    }
}
