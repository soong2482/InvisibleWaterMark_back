package com.spring.SecurityMVC.WaterMarkInfo.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.spring.SecurityMVC.CommonInfo.MultipartInputStreamFileResource;
import com.spring.SecurityMVC.LoginInfo.Service.UtilService;
import com.spring.SecurityMVC.SpringSecurity.ExceptionHandler.CustomExceptions;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkEmbed;
import com.spring.SecurityMVC.WaterMarkInfo.Domain.WatermarkLog;
import com.spring.SecurityMVC.WaterMarkInfo.Mapper.WaterMarkMapper;
import io.micrometer.common.util.StringUtils;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.time.LocalDateTime;
@Service
public class WatermarkService {
    private final UtilService utilService;
    private final WaterMarkMapper waterMarkMapper;
    public WatermarkService(UtilService utilService, WaterMarkMapper waterMarkMapper) {
        this.utilService = utilService;
        this.waterMarkMapper = waterMarkMapper;
    }
    public String extractUsernameFromSecurityContextOrCookie(HttpServletRequest request) {
        String username = utilService.getUserNameFromCookies(request);

        if (StringUtils.isBlank(username)) {
            throw new CustomExceptions.MissingRequestBodyException("Username is missing");
        }

        return username;
    }
    //-----------------------get-------------------------//
    public ResponseEntity<List<WatermarkLog>> getWaterMarkLogAll(HttpServletRequest request,HttpServletResponse response){
        String username = extractUsernameFromSecurityContextOrCookie(request);

        List<WatermarkLog> watermarkLogs = waterMarkMapper.getWaterMarkLogAll(username);
        if (watermarkLogs.isEmpty()) {
            throw new CustomExceptions.UserNotFoundException("The specified user could not be found: " + username);
        }

        return ResponseEntity.ok(watermarkLogs);
    }
    //-----------------------Embed-------------------------//
    public ResponseEntity<byte[]> embed(String data, MultipartFile imgFile, HttpServletRequest request, HttpServletResponse response) throws IOException {
        if(StringUtils.isBlank(data)){
            throw new CustomExceptions.MissingRequestBodyException("Text is missing");
        }
        ObjectMapper mapper = new ObjectMapper();
        WatermarkEmbed embed = mapper.readValue(data, WatermarkEmbed.class);
        String username = extractUsernameFromSecurityContextOrCookie(request);
        if(!embed.getUsername().equals(username)){
            throw new CustomExceptions.InvalidRequestException("Username is not equals");
        }
        String text = embed.getText();
        Random random = new Random();
        String token = hashText( 8 + random.nextInt(3));
        byte[] watermarkedImage = sendToPythonEmbed(imgFile, username, token);
        WatermarkLog watermarkLog = new WatermarkLog();
        watermarkLog.setHash(token);
        watermarkLog.setUsername(username);
        watermarkLog.setText(text);
        watermarkLog.setCreatedAt(LocalDateTime.now());
        try {
            waterMarkMapper.insertWaterMarkLog(watermarkLog);
        } catch (DuplicateKeyException e) {
            throw new CustomExceptions.UserAlreadyExistsException("Duplicate hash entry: " + e.getMessage());
        } catch (DataIntegrityViolationException e) {
            throw new CustomExceptions.DataConflictException("Watermark data integrity violation: " + e.getMessage());
        } catch (DataAccessException e) {
            throw new CustomExceptions.DatabaseException("Watermark database operation failed: " + e.getMessage());
        }
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(watermarkedImage);

    }
    public ResponseEntity<WatermarkLog> decode(MultipartFile imgFile, HttpServletRequest request, HttpServletResponse response) throws IOException {
        // 1. 파일 입력 체크
        if (imgFile == null || imgFile.isEmpty()) {
            throw new CustomExceptions.MissingRequestBodyException("Image file is missing");
        }
        String username = extractUsernameFromSecurityContextOrCookie(request);
        String watermarkedDecode = sendToPythonDecode(imgFile);
        if(watermarkedDecode.equals("decoding failed")){
            throw new CustomExceptions.DecodingFailedException("QR decoding failed");
        }else {
            WatermarkLog log = waterMarkMapper.getWaterMarkLog(watermarkedDecode)
                    .orElseThrow(() -> new CustomExceptions.ResourceNotFoundException("Watermark not found for hash: " + watermarkedDecode));
            return ResponseEntity.ok(log);
        }
    }
    public ResponseEntity<WatermarkLog> decodeVIP(MultipartFile imgFile, HttpServletRequest request, HttpServletResponse response) throws IOException {
        // 1. 파일 입력 체크
        if (imgFile == null || imgFile.isEmpty()) {
            throw new CustomExceptions.MissingRequestBodyException("Image file is missing");
        }
        String username = extractUsernameFromSecurityContextOrCookie(request);
        String watermarkedDecode = sendToPythonDecodeVIP(imgFile);
        if(watermarkedDecode.equals("decoding failed VIP")){
            throw new CustomExceptions.DecodingFailedException("QR decoding failed. VIP");
        }
//        WatermarkLog log = waterMarkMapper.getWaterMarkLog(watermarkedDecode)
//                .orElseThrow(() -> new CustomExceptions.ResourceNotFoundException("Watermark not found for hash: " + watermarkedDecode));
        WatermarkLog log = new WatermarkLog();
        log.setUsername("TestAdmin");
        log.setCreatedAt(LocalDateTime.now());
        log.setText("TestHashCode");
        log.setHash(watermarkedDecode);


        return ResponseEntity.ok(log);
    }

        public ResponseEntity<String> detectingFace(MultipartFile imgFile, HttpServletRequest request, HttpServletResponse response) throws IOException {
        String result = sendToPythonDetecting(imgFile);
        if ("ok".equalsIgnoreCase(result)) {
            return ResponseEntity.ok("Detecting Success");
        } else {
            return ResponseEntity.ok("Face not detected");
        }
    }



    //------------------------python------------------------------------//
    public byte[] sendToPythonEmbed(MultipartFile imgFile, String username, String text) throws IOException {
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

        return response.getBody();
    }
    public String sendToPythonDecode(MultipartFile imgFile) throws  IOException{
        String pythonUrl = "http://localhost:8000/decode";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", new MultipartInputStreamFileResource(imgFile.getInputStream(), imgFile.getOriginalFilename()));
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        RestTemplate restTemplate = new RestTemplate();

        ResponseEntity<String> response = restTemplate.exchange(
                pythonUrl,
                HttpMethod.POST,
                requestEntity,
                String.class
        );
        return response.getBody();
    }
    public String sendToPythonDecodeVIP(MultipartFile imgFile) throws  IOException{
        String pythonUrl = "http://localhost:8000/decodeVIP";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", new MultipartInputStreamFileResource(imgFile.getInputStream(), imgFile.getOriginalFilename()));
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        RestTemplate restTemplate = new RestTemplate();

        ResponseEntity<String> response = restTemplate.exchange(
                pythonUrl,
                HttpMethod.POST,
                requestEntity,
                String.class
        );
        return response.getBody();
    }
    public String sendToPythonDetecting(MultipartFile imgFile) throws IOException {
        String pythonUrl = "http://localhost:8000/detecting";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", new MultipartInputStreamFileResource(
                imgFile.getInputStream(), imgFile.getOriginalFilename()
        ));

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        RestTemplate restTemplate = new RestTemplate();

        ResponseEntity<String> response = restTemplate.exchange(
                pythonUrl,
                HttpMethod.POST,
                requestEntity,
                String.class
        );

        return response.getBody();
    }

    //------------Hash--------------------------------//
    public String hashText(int length) {
        String charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        SecureRandom random = new SecureRandom();

        for (int attempt = 0; attempt < 5; attempt++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < length; i++) {
                sb.append(charset.charAt(random.nextInt(charset.length())));
            }
            String tokenId = sb.toString();


            if (!waterMarkMapper.existsByTokenId(tokenId)) {
                return tokenId;
            }
        }

        throw new CustomExceptions.DataConflictException("Too many duplicate token_id collisions. Failed to generate a unique token.");
    }

}

