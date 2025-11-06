package com.spring.SecurityMVC.CommonInfo;


import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Date;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequiredArgsConstructor
public class CommonController {
    @GetMapping("${Security.backEndPoint}/test")
    public ResponseEntity<String> test(HttpServletRequest request, HttpServletResponse response) {
        return ResponseEntity.ok("test ok");
    }

    @GetMapping("/")
    public ResponseEntity<String> health(HttpServletRequest request) {
        return ResponseEntity.ok("Server is running ");
    }
}
