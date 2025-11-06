package com.spring.SecurityMVC.JwtInfo.Service;

import com.spring.SecurityMVC.SpringSecurity.ExceptionHandler.CustomExceptions;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.List;
import java.util.function.Function;

@Service
public class JwtService {
    private final RefreshTokenService refreshTokenService;
    @Value("${spring.jwt.key}")
    private String SECRET_KEY;

    public JwtService(RefreshTokenService refreshTokenService) {
        this.refreshTokenService = refreshTokenService;
    }

    public String generateAccessToken(String username, List<String> roles) {
        return Jwts.builder()
                .setSubject(username)
                .claim("roles", roles)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 30))
                .signWith(SignatureAlgorithm.HS256, SECRET_KEY)
                .compact();
    }
    public String generateRefreshToken(String username) {
        return Jwts.builder()
                .setSubject(username)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 24 * 7))
                .signWith(SignatureAlgorithm.HS256, SECRET_KEY)
                .compact();
    }

    public String getUsernameFromRequest(HttpServletRequest request) {
        String token = extractAccessTokenFromCookies(request);
        if (!validateToken(token)) {
            throw new CustomExceptions.TokenException("Access token is invalid");
        }
        Claims claims = getAllClaimsFromToken(token);
        return claims.getSubject();
    }

    public String extractAccessTokenFromCookies(HttpServletRequest request) {
        if (request.getCookies() != null) {
            for (Cookie cookie : request.getCookies()) {
                if ("Access-Token".equals(cookie.getName())) {
                    return cookie.getValue();
                }
            }
        }
        throw new CustomExceptions.MissingRequestBodyException("The accessToken cookie is missing");
    }
    public Boolean validateToken(String token) {
        return !isTokenExpired(token);
    }

    public String getUsernameFromToken(Claims claims) {
        return claims.getSubject();
    }

    public List<String> getRolesFromToken(Claims claims) {
        return claims.get("roles", List.class);
    }

    private <T> T getClaimFromToken(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = getAllClaimsFromToken(token);
        return claimsResolver.apply(claims);
    }

    public Claims getAllClaimsFromToken(String token) {
        return Jwts.parser()
                .setSigningKey(SECRET_KEY)
                .parseClaimsJws(token)
                .getBody();
    }
    private Boolean isTokenExpired(String token) {
        final Date expiration = getClaimFromToken(token, Claims::getExpiration);
        return expiration.before(new Date());
    }

    public Boolean validateRefreshToken(String token,String username) {
        String RefreshToken = refreshTokenService.getRefreshToken(username);
        if(token.equals(RefreshToken)) {
            return validateToken(token);
        }
        else{
            return false;
        }
    }
}