#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <inttypes.h>
#include <chrono>
#include <fstream>

#include "../include/tobii/tobii.h"
#include "../include/tobii/tobii_streams.h"

// Callback de gaze
void gaze_point_callback(tobii_gaze_point_t const *gaze_point, void * /* user_data */)
{
    if (gaze_point->validity == TOBII_VALIDITY_VALID)
        printf("Timestamp:%lld, Gaze point:%.6f, %.6f\n",
               (long long)gaze_point->timestamp_us, gaze_point->position_xy[0], gaze_point->position_xy[1]);
    else
        printf("Timestamp:%lld, Gaze point:%.6f, %.6f\n",
               (long long)gaze_point->timestamp_us, 0.0, 0.0);
    fflush(stdout);
}

void url_receiver(char const *url, void *user_data)
{
    char *buffer = (char *)user_data;
    if (*buffer != '\0')
        return;
    if (strlen(url) < 256)
        strcpy(buffer, url);
}

int main()
{
    printf("Iniciando gaze.exe...\n");
    fflush(stdout);
    tobii_api_t *api = NULL;
    tobii_error_t result = tobii_api_create(&api, NULL, NULL);
    assert(result == TOBII_ERROR_NO_ERROR);

    char url[256] = {0};
    result = tobii_enumerate_local_device_urls(api, url_receiver, url);
    assert(result == TOBII_ERROR_NO_ERROR);

    printf("Enumeración completada.\n");
    fflush(stdout);

    if (*url == '\0')
    {
        printf("Error: No device found\n");
        return 1;
    }

    printf("Dispositivo encontrado: %s\n", url);
    fflush(stdout);

    tobii_device_t *device = NULL;
    result = tobii_device_create(api, url, TOBII_FIELD_OF_USE_INTERACTIVE, &device);
    assert(result == TOBII_ERROR_NO_ERROR);

    result = tobii_gaze_point_subscribe(device, gaze_point_callback, 0);
    assert(result == TOBII_ERROR_NO_ERROR);

    printf("Suscripción al stream de gaze OK. Esperando datos...\n");
    fflush(stdout);

    while (true)
    {
        result = tobii_wait_for_callbacks(1, &device);
        assert(result == TOBII_ERROR_NO_ERROR || result == TOBII_ERROR_TIMED_OUT);

        result = tobii_device_process_callbacks(device);
        assert(result == TOBII_ERROR_NO_ERROR);
    }

    result = tobii_gaze_point_unsubscribe(device);
    assert(result == TOBII_ERROR_NO_ERROR);
    result = tobii_device_destroy(device);
    assert(result == TOBII_ERROR_NO_ERROR);
    result = tobii_api_destroy(api);
    assert(result == TOBII_ERROR_NO_ERROR);

    return 0;
}
