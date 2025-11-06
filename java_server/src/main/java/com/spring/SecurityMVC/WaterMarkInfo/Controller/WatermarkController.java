package com.spring.SecurityMVC.WaterMarkInfo.Controller;


import com.fasterxml.jackson.databind.ObjectMapper;
import com.spring.SecurityMVC.SpringSecurity.ExceptionHandler.CustomExceptions;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkDecode;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkEmbed;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkLog;
import com.spring.SecurityMVC.WaterMarkInfo.Service.WatermarkService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class WatermarkController {
            private final WatermarkService watermarkService;

    @PostMapping("${Security.backEndPoint}/User/DetectingFace")
    public ResponseEntity<String> DetectingFace(
            @RequestPart(value = "imgfile", required = false) MultipartFile imgFile,
            HttpServletResponse response,
            HttpServletRequest request
    ) throws IOException {
        return watermarkService.detectingFace(imgFile,request,response);
    }
    //data로 2차검증 = username받아오고 session에서 유저정보빼와서 일치시 python으로 진행
    @PostMapping(value = "${Security.backEndPoint}/User/EmbedWaterMark", consumes = "multipart/form-data")
    public ResponseEntity<byte[]> EmbedWatermark(
        @RequestPart(value = "watermarkData", required = false) String watermarkDataJson,
        @RequestPart(value = "imgfile", required = false) MultipartFile imgFile,
        HttpServletResponse response,
        HttpServletRequest request
    ) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        WatermarkEmbed watermarkData;
        try {
            watermarkData = mapper.readValue(watermarkDataJson, WatermarkEmbed.class);
        } catch (Exception e) {
            throw new CustomExceptions.InvalidRequestException("Invalid watermark data format: " + e.getMessage());
        }
        return watermarkService.embed(watermarkData, imgFile, request, response);
    }
    @PostMapping(value = "${Security.backEndPoint}/User/DecodeWaterMark", consumes = "multipart/form-data")
    public ResponseEntity<WatermarkLog> decodeWatermark(
        @RequestPart(value = "watermarkData", required = false) String watermarkDataJson,
        @RequestPart(value = "imgfile", required = false) MultipartFile imgFile,
        HttpServletRequest request,
        HttpServletResponse response
    ) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        WatermarkDecode watermarkData;
        try {
            watermarkData = mapper.readValue(watermarkDataJson, WatermarkDecode.class);
        } catch (Exception e) {
            throw new CustomExceptions.InvalidRequestException("Invalid watermark data format: " + e.getMessage());
        }
        return watermarkService.decode(imgFile, watermarkData, request, response);
    }

    @PostMapping("${Security.backEndPoint}/User/DecodeWaterMarkVIP")
    public ResponseEntity<WatermarkLog> decodeWatermarkVIP(
        @RequestPart(value = "watermarkData", required = false) String watermarkDataJson,
        @RequestPart(value = "imgfile", required = false) MultipartFile imgFile,
        HttpServletRequest request,
        HttpServletResponse response
    ) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        WatermarkEmbed watermarkData = mapper.readValue(watermarkDataJson, WatermarkEmbed.class);
        return watermarkService.decodeVIP(imgFile, watermarkData, request, response);
    }
    @GetMapping("${Security.backEndPoint}/User/getWaterMarkLog")
    public ResponseEntity<List<WatermarkLog>> getWatermarkLog(HttpServletRequest request, HttpServletResponse response) throws IOException {
        return watermarkService.getWaterMarkLogAll(request, response);
    }

}