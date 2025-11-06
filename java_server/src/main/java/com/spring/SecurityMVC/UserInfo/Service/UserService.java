package com.spring.SecurityMVC.UserInfo.Service;

import com.spring.SecurityMVC.JwtInfo.Service.JwtService;
import com.spring.SecurityMVC.LoginInfo.Service.UtilService;
import com.spring.SecurityMVC.SpringSecurity.ExceptionHandler.CustomExceptions;
import com.spring.SecurityMVC.UserInfo.Domain.User;
import com.spring.SecurityMVC.UserInfo.Domain.UserInfoResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class UserService {
    private final UtilService utilService;
    private final UserDetailsService userDetailsService;
    private final JwtService jwtService;

    public UserService(UtilService utilService, UserDetailsService userDetailsService, JwtService jwtService) {
        this.utilService = utilService;
        this.userDetailsService = userDetailsService;
        this.jwtService = jwtService;
    }

    public UserInfoResponse getUserInfo(HttpServletRequest request) {
        String username = utilService.getUserNameFromCookies(request);
        String usernameFromToken = jwtService.getUsernameFromRequest(request);
        if (!username.equals(usernameFromToken)) {
            throw new CustomExceptions.AuthenticationFailedException("Username from cookie does not match username from access token");
        }
        Optional<User> userOpt = userDetailsService.findByDetailUser(usernameFromToken);
        if (userOpt.isEmpty()) {
            throw new CustomExceptions.UserNotFoundException("The specified user could not be found: " + username);
        }
        User user = userOpt.get();
        List<String> roles = user.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();

        return new UserInfoResponse(user.getUsername(), user.getEmail(), roles,user.getApikey(),user.isApiEnabled());
    }

}
