package com.spring.SecurityMVC.WaterMarkInfo.Domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class WatermarkLog {
    private String hash;
    private String username;
    private String text;
    private LocalDateTime createdAt;
}
