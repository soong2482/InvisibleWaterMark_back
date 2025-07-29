package com.spring.SecurityMVC.SignUpInfo.Domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class SignUp {
    private String username;
    private String password;
    private String email;
    private String phone;
    private Boolean enabled;
    private String roleId;
    private String ipaddress;
    private String apikey;
    private Boolean apiEnabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
