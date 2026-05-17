namespace PlantToXmi.EAAddin.Update
{
    public sealed class UpdateResult
    {
        public UpdateResultCode Code { get; set; }
        public bool Success { get; set; }
        public string Message { get; set; }
        public string Detail { get; set; }
        public UpdateManifest Manifest { get; set; }

        public static UpdateResult From(UpdateResultCode code, string message)
        {
            return new UpdateResult
            {
                Code = code,
                Success = code == UpdateResultCode.NO_UPDATE_AVAILABLE ||
                          code == UpdateResultCode.UPDATE_AVAILABLE ||
                          code == UpdateResultCode.UPDATE_INSTALLED ||
                          code == UpdateResultCode.ROLLBACK_COMPLETED,
                Message = message,
                Detail = string.Empty
            };
        }
    }
}
