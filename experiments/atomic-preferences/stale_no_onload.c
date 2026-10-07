/* Deliberately stale ABI fixture: no JNI_OnLoad, no commit or begin symbol. */
#include <jni.h>
JNIEXPORT void JNICALL Java_atomicfixture_AtomicPreferenceFile_abort0(JNIEnv *env, jclass unused, jlong handle) {
    (void)unused; (void)handle;
    jclass type = (*env)->FindClass(env, "java/io/IOException");
    if (!type || (*env)->ExceptionCheck(env)) return;
    (*env)->ThrowNew(env, type, "atomic-session-consumed");
    (*env)->DeleteLocalRef(env, type);
}
