package com.spring.SecurityMVC.WaterMarkInfo.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.spring.SecurityMVC.CommonInfo.MultipartInputStreamFileResource;
import com.spring.SecurityMVC.LoginInfo.Service.UtilService;
import com.spring.SecurityMVC.SpringSecurity.ExceptionHandler.CustomExceptions;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkEmbed;
import io.micrometer.common.util.StringUtils;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.*;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@Service
public class WatermarkService {
    private final UtilService utilService;

    public WatermarkService(UtilService utilService) {
        this.utilService = utilService;
    }

    public ResponseEntity<byte[]> embed(String data, MultipartFile imgFile, HttpServletRequest request, HttpServletResponse response) throws IOException {
        if(StringUtils.isBlank(data)){
            throw new CustomExceptions.MissingRequestBodyException("Text is missing");
        }
        ObjectMapper mapper = new ObjectMapper();
        WatermarkEmbed embed = mapper.readValue(data, WatermarkEmbed.class);

        SecurityContextHolder.getContext().getAuthentication();
        String username = "";
        username = utilService.getUserNameFromCookies(request);

        if(StringUtils.isBlank(username)){
            throw new CustomExceptions.MissingRequestBodyException("Username is missing");
        }
        if(!embed.getUsername().equals(username)){
            throw new CustomExceptions.InvalidRequestException("Username is not equals");
        }

        byte[] watermarkedImage = sendToPython(imgFile, username, embed.getText());

        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(watermarkedImage);

    }
    public byte[] sendToPython(MultipartFile imgFile, String username, String text) throws IOException {
        String pythonUrl = "http://localhost:8000/embed";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", new MultipartInputStreamFileResource(imgFile.getInputStream(), imgFile.getOriginalFilename()));
        body.add("username", username);
        body.add("text", text);

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        RestTemplate restTemplate = new RestTemplate();
        ResponseEntity<byte[]> response = restTemplate.exchange(
                pythonUrl,
                HttpMethod.POST,
                requestEntity,
                byte[].class
        );

        return response.getBody();  // 워터마크 처리된 이미지 (바이트)
    }
}
