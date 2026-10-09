#include <stdio.h>
#include <windows.h>
#include <iostream>
#include <string>
#include <regex>
#include <winsock2.h>
#include <ws2tcpip.h>


#define SCREEN_W 1920
#define SCREEN_H 1080
#define GAZE_EXE "build\\gaze.exe"
#define UDP_IP "127.0.0.1"
#define UDP_PORT 5005

#ifdef __MINGW32__
#define popen _popen
#define pclose _pclose
#endif

int main() {
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
        std::cerr << "WSAStartup failed" << std::endl;
        return 1;
    }

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET) {
        std::cerr << "Error creando socket" << std::endl;
        WSACleanup();
        return 1;
    }

    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(UDP_PORT);
    serverAddr.sin_addr.s_addr = inet_addr(UDP_IP);

    std::cout << "Socket UDP creado para enviar a " << UDP_IP << ":" << UDP_PORT << std::endl;

    FILE* pipe = popen(GAZE_EXE, "r");
    if (!pipe) {
        std::cerr << "No se pudo ejecutar " << GAZE_EXE << std::endl;
        closesocket(sock);
        WSACleanup();
        return 1;
    } else {
        std::cout << "Ejecutando " << GAZE_EXE << "..." << std::endl;
    }

    std::regex pattern(R"(Timestamp:\s*(\d+),\s*Gaze point:\s*([0-9\.\-]+),\s*([0-9\.\-]+))");
    char buffer[512];

    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::cmatch match;
        if (std::regex_search(buffer, match, pattern)) {
            long long ts = std::stoll(match[1].str());
            int gx = static_cast<int>(std::stod(match[2].str()) * SCREEN_W);
            int gy = static_cast<int>(std::stod(match[3].str()) * SCREEN_H);

            char msg[128];
            sprintf(msg, "%lld,%d,%d", ts, gx, gy);

            sendto(sock, msg, strlen(msg), 0,
                   (sockaddr*)&serverAddr, sizeof(serverAddr));

            std::cout << "Enviado: " << msg << std::endl;
        }
        Sleep(1);
    }

    pclose(pipe);
    closesocket(sock);
    WSACleanup();
    return 0;
}
