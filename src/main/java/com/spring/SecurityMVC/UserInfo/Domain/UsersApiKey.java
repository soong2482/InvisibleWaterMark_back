package com.spring.SecurityMVC.UserInfo.Domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class UsersApiKey {
    private String username;
    private String apiKey;
    private boolean apiEnabled;
    private LocalDateTime createdAt;
}
