package com.spring.SecurityMVC.CommonInfo;


import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class CommonController {
    @GetMapping("${Security.backEndPoint}/test")
    public ResponseEntity<String> test(HttpServletRequest request, HttpServletResponse response) {
        return ResponseEntity.ok("test ok");
    }
    @GetMapping("/")
    public String health() {
        return "Server is running";
    }
}
