package com.spring.SecurityMVC.WaterMarkInfo.Controller;


import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkEmbed;
import com.spring.SecurityMVC.WaterMarkInfo.Service.WatermarkService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequiredArgsConstructor
public class WatermarkController {
    private final WatermarkService watermarkService;
    //data로 2차검증 = username받아오고 session에서 유저정보빼와서 일치시 python으로 진행
    @PostMapping("${Security.backEndPoint}/User/EmbedWaterMark")
    public ResponseEntity<byte[]> EmbedWatermark(
            @RequestPart(value = "data", required = false) String data,
            @RequestPart(value = "imgfile", required = false) MultipartFile imgFile,
            HttpServletResponse response,
            HttpServletRequest request
    ) throws IOException {
        return watermarkService.embed(data,imgFile,request,response);
    }
}