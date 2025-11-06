package com.spring.SecurityMVC.UserInfo.Controller;

import com.spring.SecurityMVC.UserInfo.Domain.UserInfoResponse;
import com.spring.SecurityMVC.UserInfo.Service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;
    @GetMapping("${Security.backEndPoint}/User/Info")
    public ResponseEntity<UserInfoResponse> getUserInfo(HttpServletRequest request) {
        UserInfoResponse userInfo = userService.getUserInfo(request);
        return ResponseEntity.ok(userInfo);
    }

}
