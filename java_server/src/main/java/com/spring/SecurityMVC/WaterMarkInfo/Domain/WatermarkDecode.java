package com.spring.SecurityMVC.WaterMarkInfo.Domain;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
@NoArgsConstructor
public class WatermarkDecode {
    private String username;
    private String apikey;
}
