package com.spring.SecurityMVC.WaterMarkInfo.Mapper;

import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkLog;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;


@Mapper
public interface WaterMarkMapper {
    void insertWaterMarkLog(WatermarkLog watermarkLog);
    List<WatermarkLog> getWaterMarkLogAll(String username);
    boolean existsByTokenId(@Param("hash") String tokenId);
}
