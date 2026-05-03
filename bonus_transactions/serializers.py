from rest_framework import serializers

from bonus_transactions.models import BonusTransactionJob, BonusTransactionJobResult


class BonusTransactionJobCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    amount = serializers.IntegerField(min_value=1, max_value=2147483647)
    start_date = serializers.DateField()
    expiration_date = serializers.DateField()
    phones_text = serializers.CharField(required=False, allow_blank=True)
    excel_file = serializers.FileField(required=False, allow_null=True)

    def validate(self, attrs):
        start_date = attrs['start_date']
        expiration_date = attrs['expiration_date']
        if expiration_date < start_date:
            raise serializers.ValidationError({'expiration_date': 'expiration_date must be greater than or equal to start_date'})

        phones_text = str(attrs.get('phones_text') or '').strip()
        excel_file = attrs.get('excel_file')

        if not phones_text and not excel_file:
            raise serializers.ValidationError('Provide manual phone numbers or Excel file')

        if excel_file is not None:
            filename = str(getattr(excel_file, 'name', '')).lower()
            if filename and not filename.endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
                raise serializers.ValidationError({'excel_file': 'Excel file must be .xlsx/.xlsm/.xltx/.xltm'})

        return attrs


class BonusTransactionJobResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusTransactionJobResult
        fields = (
            'id',
            'phone_raw',
            'phone_normalized',
            'guest_id',
            'doc_guid',
            'base_id',
            'success',
            'error_message',
            'created_at',
        )


class BonusTransactionJobListSerializer(serializers.ModelSerializer):
    initiated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = BonusTransactionJob
        fields = (
            'id',
            'description',
            'amount',
            'start_date',
            'expiration_date',
            'base_id_prefix',
            'input_source',
            'status',
            'total_phones',
            'unique_phones',
            'guests_found',
            'cashbacks_created',
            'errors_count',
            'started_at',
            'finished_at',
            'initiated_by_email',
            'created_at',
            'updated_at',
        )

    def get_initiated_by_email(self, obj):
        user = obj.initiated_by
        if user is None:
            return ''
        return str(user.email or '').strip().lower()


class BonusTransactionJobDetailSerializer(BonusTransactionJobListSerializer):
    results = BonusTransactionJobResultSerializer(many=True, read_only=True)

    class Meta(BonusTransactionJobListSerializer.Meta):
        fields = BonusTransactionJobListSerializer.Meta.fields + (
            'error_log',
            'external_api_response',
            'results',
        )
